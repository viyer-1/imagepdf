"""
Main application window with modern, professional design.
Redesigned with:
- Thumbnail grid with image previews
- Side control pane
- Drag-and-drop reordering
- Full-screen start
"""

import contextlib
import io
from pathlib import Path
from typing import List

import fitz  # For getting PDF page count
import qtawesome as qta
from PIL import Image
from PyQt6.QtCore import QPoint, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QIntValidator,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.converters import ConversionEngine
from ..utils import get_config_manager, get_logger

# Initialize logger for debugging
logger = get_logger()


class ConversionWorker(QThread):
    """Background worker for file conversions to keep UI responsive."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, conversion_func, *args):
        super().__init__()
        self.conversion_func = conversion_func
        self.args = args

    def run(self):
        try:
            self.conversion_func(*self.args)
            self.finished.emit(True, "Conversion completed successfully!")
        except Exception as e:
            self.finished.emit(False, f"Conversion failed: {str(e)}")


class ThumbnailWidget(QFrame):
    """Widget displaying a thumbnail for an image or PDF with reorder buttons."""

    delete_clicked = pyqtSignal(object)  # Emits self when delete is clicked
    move_left = pyqtSignal(int)  # Emits index when left arrow clicked
    move_right = pyqtSignal(int)  # Emits index when right arrow clicked
    position_changed = pyqtSignal(int, int)  # Emits (current_index, new_position)

    def __init__(self, file_path: str, index: int, zoom_level: float = 1.0, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.index = index
        self.zoom_level = zoom_level
        self.config = get_config_manager()
        self.base_thumbnail_size = self.config.get_app_setting("ui", "thumbnail_size", default=180)
        self.thumbnail_size = int(self.base_thumbnail_size * zoom_level)
        self.show_delete_btn = False
        self.cached_pixmap = None  # Cache for performance
        self.setup_ui()

    def set_zoom_level(self, zoom_level: float):
        """Update zoom level and resize thumbnail."""
        self.zoom_level = zoom_level
        new_size = int(self.base_thumbnail_size * zoom_level)

        # Only update if size actually changed (optimization)
        if new_size != self.thumbnail_size:
            self.thumbnail_size = new_size
            self.update_size()

    def update_size(self):
        """Update widget size based on current zoom level."""
        self.setFixedSize(self.thumbnail_size + 20, self.thumbnail_size + 140)
        self.image_label.setFixedSize(self.thumbnail_size, self.thumbnail_size)

        # Use cached pixmap if available, otherwise generate
        if self.cached_pixmap is None:
            self.cached_pixmap = self.generate_thumbnail(cache_size=True)

        # Scale the cached pixmap instead of regenerating
        scaled_pixmap = self.cached_pixmap.scaled(
            self.thumbnail_size,
            self.thumbnail_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pixmap)

        # Reposition badges
        self.delete_btn.move(self.width() - 30, 4)
        self.type_badge.move(6, self.thumbnail_size - 22)

    def setup_ui(self):
        """Setup the thumbnail UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.is_being_dragged = False  # Track drag state for visual feedback
        self.setStyleSheet("""
            ThumbnailWidget {
                border: 2px solid #e1e8ed;
                border-radius: 12px;
                background-color: white;
                padding: 5px;
            }
            ThumbnailWidget:hover {
                border: 2px solid transparent;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                padding: 2px;
            }
        """)
        self.setFixedSize(
            self.thumbnail_size + 20, self.thumbnail_size + 140
        )  # Increased for position + arrows

        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Thumbnail image container
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(self.thumbnail_size, self.thumbnail_size)
        self.image_label.setStyleSheet("""
            border: none;
            background-color: #f8f9fa;
            border-radius: 8px;
        """)

        # Generate and set thumbnail
        pixmap = self.generate_thumbnail()
        self.image_label.setPixmap(pixmap)
        layout.addWidget(self.image_label)

        # Delete button (overlay on top-right)
        self.delete_btn = QPushButton(self)  # Parent to main widget, not layout
        self.delete_btn.setIcon(qta.icon("fa5s.times", color="white"))
        self.delete_btn.setFixedSize(26, 26)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff6b6b, stop:1 #ee5a6f);
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff5252, stop:1 #f44336);
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self))
        self.delete_btn.move(self.width() - 30, 4)
        self.delete_btn.raise_()  # Ensure it's on top
        self.delete_btn.hide()

        # File type badge (bottom-left overlay on image)
        file_ext = Path(self.file_path).suffix.lower().replace(".", "").upper()
        badge_colors = {
            "PDF": ("#e74c3c", "#c0392b"),
            "JPG": ("#3498db", "#2980b9"),
            "JPEG": ("#3498db", "#2980b9"),
            "PNG": ("#9b59b6", "#8e44ad"),
            "TIFF": ("#16a085", "#138d75"),
            "TIF": ("#16a085", "#138d75"),
            "WEBP": ("#2ecc71", "#27ae60"),
            "BMP": ("#e67e22", "#d35400"),
        }
        color_start, color_end = badge_colors.get(file_ext, ("#95a5a6", "#7f8c8d"))

        self.type_badge = QLabel(file_ext)
        self.type_badge.setFont(QFont("Inter", 7, QFont.Weight.Bold))
        self.type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type_badge.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {color_start}, stop:1 {color_end});
            color: white;
            border-radius: 4px;
            padding: 2px 6px;
            border: none;
        """)
        self.type_badge.setParent(self.image_label)
        self.type_badge.move(6, self.thumbnail_size - 22)
        self.type_badge.adjustSize()

        # File name label
        file_name = Path(self.file_path).name
        if len(file_name) > 22:
            file_name = file_name[:19] + "..."
        self.name_label = QLabel(file_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(QFont("Inter", 9, QFont.Weight.Medium))
        self.name_label.setStyleSheet("border: none; color: #2c3e50;")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        # File size label
        try:
            file_size = Path(self.file_path).stat().st_size
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"

            self.size_label = QLabel(size_str)
            self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.size_label.setFont(QFont("Inter", 7))
            self.size_label.setStyleSheet("border: none; color: #95a5a6;")
            layout.addWidget(self.size_label)
        except Exception:
            pass

        # Position number input (editable)
        self.position_input = QLineEdit(f"{self.index + 1}")
        self.position_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.position_input.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.position_input.setFixedWidth(50)
        self.position_input.setMaxLength(3)  # Max 3 digits
        self.position_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #667eea;
                color: #667eea;
                background: rgba(102, 126, 234, 0.1);
                border-radius: 4px;
                padding: 2px 8px;
                text-align: center;
            }
            QLineEdit:focus {
                background: white;
                border: 2px solid #667eea;
            }
        """)
        # Use validator to only allow numbers (no input mask to avoid spaces)
        validator = QIntValidator(1, 999, self)
        self.position_input.setValidator(validator)

        # Connect signals
        self.position_input.returnPressed.connect(self.on_position_changed)
        self.position_input.editingFinished.connect(self.on_position_changed)
        layout.addWidget(self.position_input, alignment=Qt.AlignmentFlag.AlignCenter)

        # Arrow buttons container
        arrow_container = QWidget()
        arrow_container.setStyleSheet("background: transparent; border: none;")
        arrow_layout = QHBoxLayout()
        arrow_layout.setSpacing(8)
        arrow_layout.setContentsMargins(0, 4, 0, 0)
        arrow_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Left arrow button
        self.left_btn = QPushButton()
        self.left_btn.setIcon(qta.icon("fa5s.chevron-left", color="#667eea"))
        self.left_btn.setFixedSize(32, 28)
        self.left_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 2px solid #667eea;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #667eea;
            }
            QPushButton:hover QIcon {
                color: white;
            }
            QPushButton:disabled {
                background: #f5f7fa;
                border: 2px solid #dfe6e9;
            }
        """)
        self.left_btn.clicked.connect(lambda: self.move_left.emit(self.index))
        arrow_layout.addWidget(self.left_btn)

        # Right arrow button
        self.right_btn = QPushButton()
        self.right_btn.setIcon(qta.icon("fa5s.chevron-right", color="#667eea"))
        self.right_btn.setFixedSize(32, 28)
        self.right_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 2px solid #667eea;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #667eea;
            }
            QPushButton:hover QIcon {
                color: white;
            }
            QPushButton:disabled {
                background: #f5f7fa;
                border: 2px solid #dfe6e9;
            }
        """)
        self.right_btn.clicked.connect(lambda: self.move_right.emit(self.index))
        arrow_layout.addWidget(self.right_btn)

        arrow_container.setLayout(arrow_layout)
        layout.addWidget(arrow_container)

        self.setLayout(layout)

        # DON'T accept drops on individual thumbnails - let workspace handle it
        self.setAcceptDrops(False)

        # Enable mouse tracking for better drag detection
        self.setMouseTracking(False)  # Don't need continuous tracking, just button events

        # Ensure widget can receive mouse events
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # Enhanced shadow for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        """Show delete button on hover."""
        self.delete_btn.show()
        self.delete_btn.raise_()  # Ensure it stays on top
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide delete button when not hovering."""
        self.delete_btn.hide()
        super().leaveEvent(event)

    def generate_thumbnail(self, cache_size: bool = False) -> QPixmap:
        """Generate thumbnail from image or PDF.

        Args:
            cache_size: If True, generate at larger size for caching (540px = 3x base size)
        """
        try:
            target_size = 540 if cache_size else self.thumbnail_size
            file_ext = Path(self.file_path).suffix.lower()

            if file_ext == ".pdf":
                # Generate thumbnail from first page of PDF
                doc = fitz.open(self.file_path)
                if len(doc) > 0:
                    page = doc[0]
                    zoom = target_size / max(page.rect.width, page.rect.height)
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)

                    # Convert to QPixmap
                    img_data = pix.tobytes("png")
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    doc.close()

                    return pixmap.scaled(
                        target_size,
                        target_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
            else:
                # Generate thumbnail from image
                img = Image.open(self.file_path)
                img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)

                # Convert to QPixmap
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="PNG")
                pixmap = QPixmap()
                pixmap.loadFromData(img_byte_arr.getvalue())

                return pixmap

        except Exception as e:
            print(f"Error generating thumbnail for {self.file_path}: {e}")

        # Return placeholder if thumbnail generation fails
        pixmap = QPixmap(target_size, target_size)
        pixmap.fill(Qt.GlobalColor.lightGray)
        return pixmap

    def update_position(self, new_index: int, total_items: int):
        """Update position input and button states based on new index.

        Args:
            new_index: New position in the list (0-indexed)
            total_items: Total number of items in the list
        """
        self.index = new_index
        self.total_items = total_items

        # Block signals to prevent triggering position_changed while updating
        self.position_input.blockSignals(True)
        self.position_input.setText(f"{new_index + 1}")
        self.position_input.blockSignals(False)

        # Disable left button if at start
        self.left_btn.setEnabled(new_index > 0)

        # Disable right button if at end
        self.right_btn.setEnabled(new_index < total_items - 1)

    def on_position_changed(self):
        """Handle when user enters a new position number."""
        # Prevent duplicate processing if called multiple times
        if hasattr(self, "_processing_position_change") and self._processing_position_change:
            return

        self._processing_position_change = True

        try:
            # Get the entered text and strip whitespace
            text = self.position_input.text().strip()
            if not text:
                # If empty, restore current position
                self.position_input.blockSignals(True)
                self.position_input.setText(f"{self.index + 1}")
                self.position_input.blockSignals(False)
                self.position_input.clearFocus()  # Remove focus to deselect
                return

            # Parse the new position (1-indexed from user)
            new_position = int(text)

            # Validate range (1 to total_items)
            if new_position < 1:
                new_position = 1
            elif hasattr(self, "total_items") and new_position > self.total_items:
                new_position = self.total_items

            # Convert to 0-indexed
            new_index = new_position - 1

            # Only emit if position actually changed
            if new_index != self.index:
                self.position_changed.emit(self.index, new_index)
                self.position_input.clearFocus()  # Remove focus after change
            else:
                # Restore original value if no change
                self.position_input.blockSignals(True)
                self.position_input.setText(f"{self.index + 1}")
                self.position_input.blockSignals(False)
                self.position_input.clearFocus()

        except ValueError:
            # Invalid input, restore current position
            self.position_input.blockSignals(True)
            self.position_input.setText(f"{self.index + 1}")
            self.position_input.blockSignals(False)
            self.position_input.clearFocus()
        finally:
            self._processing_position_change = False


class UnifiedWorkspaceWidget(QScrollArea):
    """Unified workspace that always accepts drops, shows thumbnails with zoom support."""

    files_dropped = pyqtSignal(list)  # External files dropped
    order_changed = pyqtSignal(int, int)  # old_index, new_index
    thumbnail_deleted = pyqtSignal(int)  # index of deleted thumbnail
    zoom_changed = pyqtSignal(int)  # zoom level changed (as percentage)
    browse_clicked = pyqtSignal()  # placeholder clicked to browse

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnails = []
        self.zoom_level = 1.0
        self.is_panning = False
        self.last_pan_point = QPoint()
        self.drag_source_index = None
        self.drop_indicator_index = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the workspace UI."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Enable drops on workspace
        self.setAcceptDrops(True)
        logger.info("[WORKSPACE] ✓ Drop acceptance enabled on workspace")

        # Ensure the container widget also accepts drops
        # This is set after container is created

        # Premium gradient background
        self.setStyleSheet("""
            QScrollArea {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f5f7fa, stop:0.5 #c3cfe2, stop:1 #f5f7fa);
                border: none;
            }
        """)

        # Container widget
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container.setAcceptDrops(True)  # Also enable drops on container
        logger.debug("[WORKSPACE] ✓ Drop acceptance enabled on container")
        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Premium placeholder with gradient border
        self.placeholder = QFrame()
        self.placeholder.setStyleSheet("""
            QFrame {
                border: 3px dashed transparent;
                border-radius: 16px;
                background-image: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(102, 126, 234, 0.1),
                    stop:1 rgba(118, 75, 162, 0.1));
            }
        """)
        placeholder_layout = QVBoxLayout()
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.setSpacing(20)

        # Large gradient icon
        icon_container = QWidget()
        icon_container.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #667eea, stop:1 #764ba2);
            border-radius: 50px;
        """)
        icon_container.setFixedSize(100, 100)
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.cloud-upload-alt", color="white").pixmap(QSize(50, 50)))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        icon_layout.addWidget(icon_label)
        icon_container.setLayout(icon_layout)
        placeholder_layout.addWidget(icon_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Main text with gradient
        text_label = QLabel("Drop Your Files Here")
        text_label.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet("""
            color: #2c3e50;
            border: none;
            background: transparent;
        """)
        placeholder_layout.addWidget(text_label)

        # Subtitle
        subtitle = QLabel("or click Browse Files to get started")
        subtitle.setFont(QFont("Inter", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; border: none; background: transparent;")
        placeholder_layout.addWidget(subtitle)

        # Supported formats hint (dynamic)
        self.formats_hint = QLabel("Supports: JPG, PNG, TIFF")
        self.formats_hint.setFont(QFont("Inter", 9))
        self.formats_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.formats_hint.setStyleSheet("""
            color: #95a5a6;
            border: none;
            background: rgba(255, 255, 255, 0.5);
            padding: 6px 12px;
            border-radius: 12px;
        """)
        placeholder_layout.addWidget(self.formats_hint)

        self.placeholder.setLayout(placeholder_layout)
        self.placeholder.setMinimumHeight(400)
        self.placeholder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.placeholder.mousePressEvent = lambda e: self.browse_clicked.emit()  # Make clickable
        self.layout.addWidget(self.placeholder)

        # Grid layout for thumbnails (hidden initially)
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background-color: transparent;")
        self.grid_widget.setAcceptDrops(True)  # Allow drops on grid
        logger.debug("[WORKSPACE] ✓ Drop acceptance enabled on grid widget")
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.grid_widget.setLayout(self.grid_layout)
        self.grid_widget.setVisible(False)
        self.layout.addWidget(self.grid_widget)

        self.container.setLayout(self.layout)
        self.setWidget(self.container)

    def add_thumbnail(self, file_path: str):
        """Add a thumbnail to the workspace."""
        index = len(self.thumbnails)
        thumbnail = ThumbnailWidget(file_path, index, self.zoom_level)
        thumbnail.delete_clicked.connect(self.on_thumbnail_delete)
        thumbnail.move_left.connect(self.on_move_left)
        thumbnail.move_right.connect(self.on_move_right)
        thumbnail.position_changed.connect(self.on_position_changed)
        self.thumbnails.append(thumbnail)
        self.refresh_grid()

    def add_thumbnails(self, file_paths: List[str]):
        """Add multiple thumbnails."""
        for file_path in file_paths:
            self.add_thumbnail(file_path)

    def on_thumbnail_delete(self, thumbnail):
        """Handle thumbnail deletion."""
        if thumbnail in self.thumbnails:
            index = self.thumbnails.index(thumbnail)
            self.thumbnails.remove(thumbnail)
            thumbnail.deleteLater()
            self.thumbnail_deleted.emit(index)
            self.refresh_grid()

    def on_move_left(self, index: int):
        """Handle moving thumbnail to the left (earlier in order)."""
        if index > 0:
            # Swap with previous item
            self.thumbnails[index], self.thumbnails[index - 1] = (
                self.thumbnails[index - 1],
                self.thumbnails[index],
            )

            # Update positions and button states
            self.update_all_positions()

            # Emit signal for external tracking
            self.order_changed.emit(index, index - 1)

            # Refresh the display
            self.refresh_grid()

    def on_move_right(self, index: int):
        """Handle moving thumbnail to the right (later in order)."""
        if index < len(self.thumbnails) - 1:
            # Swap with next item
            self.thumbnails[index], self.thumbnails[index + 1] = (
                self.thumbnails[index + 1],
                self.thumbnails[index],
            )

            # Update positions and button states
            self.update_all_positions()

            # Emit signal for external tracking
            self.order_changed.emit(index, index + 1)

            # Refresh the display
            self.refresh_grid()

    def on_position_changed(self, current_index: int, new_index: int):
        """Handle when user enters a new position for a thumbnail.

        Args:
            current_index: Current position (0-indexed)
            new_index: Desired new position (0-indexed)
        """
        # Validate indices
        if not (0 <= current_index < len(self.thumbnails)):
            return
        if not (0 <= new_index < len(self.thumbnails)):
            return

        # No need to move if same position
        if current_index == new_index:
            return

        # Remove thumbnail from current position
        thumbnail = self.thumbnails.pop(current_index)

        # Insert at new position
        self.thumbnails.insert(new_index, thumbnail)

        # Update all positions and button states
        self.update_all_positions()

        # Emit signal for external tracking
        self.order_changed.emit(current_index, new_index)

        # Refresh the display
        self.refresh_grid()

    def update_all_positions(self):
        """Update position labels and button states for all thumbnails."""
        total = len(self.thumbnails)
        for i, thumb in enumerate(self.thumbnails):
            thumb.update_position(i, total)

    def remove_thumbnail(self, index: int):
        """Remove a thumbnail by index."""
        if 0 <= index < len(self.thumbnails):
            thumbnail = self.thumbnails.pop(index)
            thumbnail.deleteLater()
            self.refresh_grid()

    def clear_thumbnails(self):
        """Remove all thumbnails."""
        for thumbnail in self.thumbnails:
            thumbnail.deleteLater()
        self.thumbnails.clear()
        self.refresh_grid()

    def get_file_paths(self) -> List[str]:
        """Get list of file paths in current order."""
        return [thumb.file_path for thumb in self.thumbnails]

    def set_zoom_level(self, zoom_level: float):
        """Update zoom level for all thumbnails (optimized)."""
        new_zoom = max(0.6, min(3.0, zoom_level))

        # Only update if zoom actually changed
        if abs(new_zoom - self.zoom_level) < 0.01:
            return

        self.zoom_level = new_zoom

        # Batch update all thumbnails
        for thumbnail in self.thumbnails:
            thumbnail.set_zoom_level(self.zoom_level)

        # Refresh grid layout once after all updates
        self.refresh_grid()

    def update_format_hint(self, text: str):
        """Update the format hint text in placeholder."""
        self.formats_hint.setText(text)

    def refresh_grid(self):
        """Refresh the grid layout."""
        # Clear existing layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Show placeholder if no thumbnails
        if not self.thumbnails:
            self.placeholder.setVisible(True)
            self.grid_widget.setVisible(False)
            return

        # Hide placeholder and show grid
        self.placeholder.setVisible(False)
        self.grid_widget.setVisible(True)

        # Determine columns based on zoom level
        if self.zoom_level >= 2.5:
            columns = 1  # Vertical layout at max zoom (like PDF)
        elif self.zoom_level >= 1.5:
            columns = 3
        elif self.zoom_level >= 0.8:
            columns = 5
        else:
            columns = 7

        # Add thumbnails to grid
        total = len(self.thumbnails)
        for idx, thumbnail in enumerate(self.thumbnails):
            thumbnail.index = idx
            thumbnail.update_position(idx, total)  # Update position label and buttons
            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(thumbnail, row, col)

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming (Ctrl+Scroll)."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom with Ctrl+Scroll
            delta = event.angleDelta().y()
            zoom_change = 0.1 if delta > 0 else -0.1
            new_zoom = self.zoom_level + zoom_change
            self.set_zoom_level(new_zoom)
            # Emit signal to update slider
            self.zoom_changed.emit(int(new_zoom * 100))
            event.accept()
        else:
            # Normal scrolling
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press for panning."""
        # Only start panning if clicking on empty space (not on thumbnails)
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            # Check if we clicked on a thumbnail
            clicked_on_thumbnail = False
            for thumb in self.thumbnails:
                if thumb.geometry().contains(self.widget().mapFrom(self, event.pos())):
                    clicked_on_thumbnail = True
                    break

            if not clicked_on_thumbnail:
                self.is_panning = True
                self.last_pan_point = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for panning."""
        if self.is_panning:
            delta = event.pos() - self.last_pan_point
            self.last_pan_point = event.pos()

            # Scroll the view
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release for panning."""
        if self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event (external files only)."""
        logger.info("[WORKSPACE] 📥 Drag entered workspace")
        logger.debug(f"[WORKSPACE] Mime data formats: {event.mimeData().formats()}")
        logger.debug(f"[WORKSPACE] Has URLs: {event.mimeData().hasUrls()}")

        if event.mimeData().hasUrls():
            # External files
            logger.info("[WORKSPACE] ✅ Accepting external file drop")
            urls = event.mimeData().urls()
            logger.debug(f"[WORKSPACE] URLs: {[url.toLocalFile() for url in urls]}")
            event.acceptProposedAction()
        else:
            logger.warning("[WORKSPACE] ❌ Ignoring drag - unknown mime type")
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move (external files only)."""
        if event.mimeData().hasUrls():
            logger.debug("[WORKSPACE] Drag move - external files")
            event.acceptProposedAction()
        else:
            logger.debug("[WORKSPACE] Drag move - ignoring")
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event (external files only)."""
        logger.info("[WORKSPACE] 🎯 Drop event triggered")

        if event.mimeData().hasUrls():
            # External file drop - emit signal to let MainWindow handle validation
            logger.info("[WORKSPACE] Processing external file drop")
            files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if Path(file_path).is_file():
                    files.append(file_path)

            logger.info(f"[WORKSPACE] ✅ Accepting {len(files)} external files")
            if files:
                self.files_dropped.emit(files)
                event.acceptProposedAction()
        else:
            logger.warning("[WORKSPACE] ❌ Drop ignored - unknown mime type")
            event.ignore()


class CustomPageSizeDialog(QDialog):
    """Dialog for entering custom page size."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Page Size")
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()

        # Instructions
        label = QLabel("Enter custom page size in points (72 points = 1 inch):")
        layout.addWidget(label)

        # Width input
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        self.width_input = QLineEdit()
        self.width_input.setPlaceholderText("e.g., 612")
        width_layout.addWidget(self.width_input)
        width_layout.addWidget(QLabel("points"))
        layout.addLayout(width_layout)

        # Height input
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height:"))
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("e.g., 792")
        height_layout.addWidget(self.height_input)
        height_layout.addWidget(QLabel("points"))
        layout.addLayout(height_layout)

        # Common sizes hint
        hint = QLabel("\nCommon sizes:\nA4: 595 × 842\nLetter: 612 × 792\nLegal: 612 × 1008")
        hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        layout.addWidget(hint)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_size(self):
        """Get the entered size as tuple (width, height) in points."""
        try:
            width = float(self.width_input.text())
            height = float(self.height_input.text())
            return (width, height)
        except ValueError:
            return None


class MainWindow(QMainWindow):
    """Main application window with modern layout."""

    def __init__(self):
        super().__init__()
        self.config = get_config_manager()
        self.conversion_engine = ConversionEngine()
        self.file_list = []
        self.conversion_worker = None
        self.custom_page_size = None

        # Zoom debouncing timer for performance
        self.zoom_timer = QTimer()
        self.zoom_timer.setSingleShot(True)
        self.zoom_timer.setInterval(50)  # 50ms debounce
        self.zoom_timer.timeout.connect(self.apply_zoom)
        self.pending_zoom_level = None

        # Setup UI
        self.setup_ui()

        # Show the window
        if self.config.get_app_setting("window", "start_maximized", default=True):
            self.showMaximized()
        else:
            self.show()

        # Get app name from config
        app_name = self.config.get_app_setting("branding", "app_name", default="Image ↔ PDF Converter")
        self.setWindowTitle(app_name)

        # Set window size (but don't show yet)
        min_width = self.config.get_app_setting("window", "min_width", default=1000)
        min_height = self.config.get_app_setting("window", "min_height", default=700)
        self.setMinimumSize(min_width, min_height)
        self.resize(1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout - horizontal split
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Content area (left side)
        content_widget = self.create_content_area()
        main_layout.addWidget(content_widget, stretch=1)

        # Control pane (right side)
        control_pane = self.create_control_pane()
        pane_width = self.config.get_app_setting("ui", "control_pane_width", default=350)
        control_pane.setFixedWidth(pane_width)
        main_layout.addWidget(control_pane)

        central_widget.setLayout(main_layout)

    def create_content_area(self) -> QWidget:
        """Create the main content area with unified workspace."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header = self.create_header()
        layout.addWidget(header)

        # Workspace label with modern styling
        files_label = QLabel("Workspace")
        files_label.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        files_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 8px 0px;
                background-color: transparent;
            }
        """)
        layout.addWidget(files_label)

        # Unified workspace
        self.workspace = UnifiedWorkspaceWidget()
        self.workspace.files_dropped.connect(self.add_files)
        self.workspace.order_changed.connect(self.on_thumbnails_reordered)
        self.workspace.thumbnail_deleted.connect(self.on_thumbnail_deleted)
        self.workspace.zoom_changed.connect(self.on_workspace_zoom_changed)
        self.workspace.browse_clicked.connect(self.browse_files)
        layout.addWidget(self.workspace, stretch=1)

        widget.setLayout(layout)
        return widget

    def create_control_pane(self) -> QWidget:
        """Create the right control pane with glassmorphism."""
        pane = QFrame()
        pane.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.95),
                    stop:1 rgba(248, 249, 250, 0.95));
                border-left: 1px solid rgba(222, 226, 230, 0.5);
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Conversion Settings")
        title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        # Direction selector with consistent styling
        direction_label = QLabel("Direction:")
        direction_label.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        layout.addWidget(direction_label)
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Images → PDF", "PDF → Images"])
        self.direction_combo.setFont(QFont("Inter", 10))
        self.direction_combo.setMinimumHeight(38)
        self.direction_combo.setStyleSheet(self.get_combobox_style())
        self.direction_combo.currentIndexChanged.connect(self.on_direction_changed)
        layout.addWidget(self.direction_combo)

        layout.addSpacing(10)

        # Options container (changes based on direction)
        self.options_container = QWidget()
        self.options_layout = QVBoxLayout()
        self.options_layout.setSpacing(10)
        self.options_container.setLayout(self.options_layout)
        layout.addWidget(self.options_container)

        # Initialize options
        self.on_direction_changed()

        layout.addSpacing(20)

        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("background-color: #dee2e6;")
        layout.addWidget(separator1)

        layout.addSpacing(10)

        # Workspace controls
        workspace_label = QLabel("Workspace Controls:")
        workspace_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        workspace_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(workspace_label)

        # Zoom controls
        zoom_container = QWidget()
        zoom_layout = QVBoxLayout()
        zoom_layout.setSpacing(8)

        zoom_label_layout = QHBoxLayout()
        zoom_lbl = QLabel("Zoom:")
        zoom_lbl.setFont(QFont("Inter", 10, QFont.Weight.Medium))
        zoom_label_layout.addWidget(zoom_lbl)
        zoom_label_layout.addStretch()

        # Zoom percentage input
        self.zoom_input = QLineEdit()
        self.zoom_input.setPlaceholderText("100")
        self.zoom_input.setMaximumWidth(60)
        self.zoom_input.setFont(QFont("Inter", 9))
        self.zoom_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e1e8ed;
                border-radius: 6px;
                padding: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        self.zoom_input.returnPressed.connect(self.on_zoom_input_changed)
        zoom_label_layout.addWidget(self.zoom_input)
        percent_lbl = QLabel("%")
        percent_lbl.setFont(QFont("Inter", 9))
        zoom_label_layout.addWidget(percent_lbl)
        zoom_layout.addLayout(zoom_label_layout)

        # Zoom slider with custom styling
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(60)  # 60%
        self.zoom_slider.setMaximum(300)  # 300%
        self.zoom_slider.setValue(100)  # 100%
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom_slider.setTickInterval(50)
        self.zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #e1e8ed;
                height: 6px;
                background: white;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5568d3, stop:1 #6a3f8f);
            }
        """)
        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        zoom_layout.addWidget(self.zoom_slider)

        # Zoom hint with better formatting
        zoom_hint = QLabel("Ctrl+Scroll to zoom • Ctrl+Drag to pan")
        zoom_hint.setFont(QFont("Inter", 8))
        zoom_hint.setStyleSheet("color: #7f8c8d;")
        zoom_hint.setWordWrap(True)
        zoom_layout.addWidget(zoom_hint)

        zoom_container.setLayout(zoom_layout)
        layout.addWidget(zoom_container)

        # Modern file action buttons with proper icons
        browse_btn = QPushButton("  Browse Files")
        browse_btn.setIcon(qta.icon("fa5s.folder-open", color="#2c3e50"))
        browse_btn.setIconSize(QSize(16, 16))
        browse_btn.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        browse_btn.setMinimumHeight(40)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 8px 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
                border-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #d5dbdb;
            }
        """)
        browse_btn.clicked.connect(self.browse_files)
        layout.addWidget(browse_btn)

        clear_btn = QPushButton("  Clear All")
        clear_btn.setIcon(qta.icon("fa5s.trash-alt", color="#e74c3c"))
        clear_btn.setIconSize(QSize(16, 16))
        clear_btn.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        clear_btn.setMinimumHeight(40)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #e74c3c;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                padding: 8px 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #fadbd8;
                border-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #f1948a;
            }
        """)
        clear_btn.clicked.connect(self.clear_files)
        layout.addWidget(clear_btn)

        layout.addStretch()

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #dee2e6;")
        layout.addWidget(separator2)

        layout.addSpacing(10)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Convert button (at bottom) with proper icon
        self.convert_btn = QPushButton("  Convert Files")
        self.convert_btn.setIcon(qta.icon("fa5s.magic", color="white"))
        self.convert_btn.setIconSize(QSize(18, 18))
        self.convert_btn.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self.convert_btn.setMinimumHeight(55)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 10px;
                padding: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.convert_btn.clicked.connect(self.convert_files)

        # Add shadow to convert button for prominence
        convert_btn_shadow = QGraphicsDropShadowEffect()
        convert_btn_shadow.setBlurRadius(20)
        convert_btn_shadow.setColor(QColor(52, 152, 219, 120))
        convert_btn_shadow.setOffset(0, 4)
        self.convert_btn.setGraphicsEffect(convert_btn_shadow)

        layout.addWidget(self.convert_btn)

        pane.setLayout(layout)

        # Add shadow to control pane for depth
        pane_shadow = QGraphicsDropShadowEffect()
        pane_shadow.setBlurRadius(20)
        pane_shadow.setColor(QColor(0, 0, 0, 50))
        pane_shadow.setOffset(-3, 0)
        pane.setGraphicsEffect(pane_shadow)

        return pane

    def get_combobox_style(self):
        """Get consistent combobox styling."""
        return """
            QComboBox {
                border: 2px solid #e1e8ed;
                border-radius: 8px;
                padding: 6px 12px;
                background-color: white;
                color: #2c3e50;
                font-family: Inter;
                font-size: 10pt;
            }
            QComboBox:hover {
                border-color: #667eea;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #667eea;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #5a6c7d;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #667eea;
                border-radius: 8px;
                background-color: white;
                color: #2c3e50;
                selection-background-color: #667eea;
                selection-color: white;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                color: #2c3e50;
                background-color: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e8eaf6;
                color: #2c3e50;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #667eea;
                color: white;
            }
        """

    def on_workspace_zoom_changed(self, value: int):
        """Handle zoom change from workspace (Ctrl+Scroll)."""
        self.zoom_slider.blockSignals(True)  # Prevent feedback loop
        self.zoom_slider.setValue(value)
        self.zoom_input.setText(str(value))
        self.zoom_slider.blockSignals(False)

    def on_zoom_slider_changed(self, value: int):
        """Handle zoom slider change with debouncing."""
        self.zoom_input.setText(str(value))
        self.pending_zoom_level = value / 100.0

        # Debounce: restart timer on each change
        self.zoom_timer.stop()
        self.zoom_timer.start()

    def apply_zoom(self):
        """Apply the pending zoom level (called after debounce)."""
        if self.pending_zoom_level is not None:
            self.workspace.set_zoom_level(self.pending_zoom_level)
            self.pending_zoom_level = None

    def on_zoom_input_changed(self):
        """Handle zoom input text change."""
        try:
            text = self.zoom_input.text().strip().replace("%", "")
            value = int(text)
            value = max(30, min(300, value))  # Clamp to range
            self.zoom_slider.setValue(value)
            # Zoom will be applied through slider's debounced handler
        except ValueError:
            # Invalid input, reset to current slider value
            self.zoom_input.setText(str(self.zoom_slider.value()))

    def create_header(self) -> QWidget:
        """Create the header with privacy-focused branding and user info."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1a2332;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QHBoxLayout()

        # App name with shield icon
        app_name_layout = QHBoxLayout()
        app_name_layout.setSpacing(8)

        shield_icon = QLabel()
        shield_icon.setPixmap(qta.icon("fa5s.shield-alt", color="#27ae60").pixmap(QSize(24, 24)))
        app_name_layout.addWidget(shield_icon)

        app_name = self.config.get_app_setting("app_name", default="Image ↔ PDF Converter")
        title = QLabel(app_name)
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        app_name_layout.addWidget(title)

        # Privacy tagline
        tagline = QLabel("Your files never leave your computer")
        tagline.setFont(QFont("Inter", 9))
        tagline.setStyleSheet("color: #95a5a6; margin-left: 10px;")
        app_name_layout.addWidget(tagline)

        layout.addLayout(app_name_layout)
        layout.addStretch()

        # Local processing badge
        local_processing_btn = QPushButton(" Local")
        local_processing_btn.setIcon(qta.icon("fa5s.lock", color="#27ae60"))
        local_processing_btn.setIconSize(QSize(12, 12))
        local_processing_btn.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        local_processing_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(39, 174, 96, 0.2);
                border: 2px solid #27ae60;
                color: #27ae60;
                border-radius: 12px;
                padding: 5px 12px;
            }
        """)
        local_processing_btn.setEnabled(False)  # Non-clickable
        local_processing_btn.setFlat(True)
        layout.addWidget(local_processing_btn)

        # Open Source Badge
        oss_badge = QPushButton(" Open Source")
        oss_badge.setIcon(qta.icon("fa5s.code-branch", color="white"))
        oss_badge.setIconSize(QSize(12, 12))
        oss_badge.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        oss_badge.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 12px;
                padding: 5px 12px;
            }
        """)
        oss_badge.setEnabled(False)
        layout.addWidget(oss_badge)

        header.setLayout(layout)

        # Add shadow to header for depth
        header_shadow = QGraphicsDropShadowEffect()
        header_shadow.setBlurRadius(15)
        header_shadow.setColor(QColor(0, 0, 0, 60))
        header_shadow.setOffset(0, 3)
        header.setGraphicsEffect(header_shadow)

        return header

    def on_direction_changed(self):
        """Update options based on conversion direction."""
        # Clear existing options
        while self.options_layout.count():
            item = self.options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        direction = self.direction_combo.currentText()

        # Update format hints in placeholder
        format_hint = self.get_format_hint_text(direction)
        self.workspace.update_format_hint(format_hint)

        if "→ PDF" in direction:
            # Images to PDF options
            page_size_label = QLabel("Page Size:")
            page_size_label.setFont(QFont("Inter", 10, QFont.Weight.Medium))
            self.options_layout.addWidget(page_size_label)
            self.page_size_combo = QComboBox()
            self.page_size_combo.addItems(["A4", "Letter", "Legal", "Original", "Custom..."])
            self.page_size_combo.setMinimumHeight(38)
            self.page_size_combo.setStyleSheet(self.get_combobox_style())
            self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
            self.options_layout.addWidget(self.page_size_combo)

        else:
            # PDF to Images options
            format_label = QLabel("Output Format:")
            format_label.setFont(QFont("Inter", 10, QFont.Weight.Medium))
            self.options_layout.addWidget(format_label)
            self.format_combo = QComboBox()

            # All formats available in Open Source
            available_formats = ["JPG", "PNG", "TIFF"]
            self.format_combo.addItems(available_formats)
            self.format_combo.setMinimumHeight(38)
            self.format_combo.setStyleSheet(self.get_combobox_style())
            self.options_layout.addWidget(self.format_combo)

            # DPI selection
            dpi_label = QLabel("Quality (DPI):")
            dpi_label.setFont(QFont("Inter", 10, QFont.Weight.Medium))
            self.options_layout.addWidget(dpi_label)
            self.dpi_combo = QComboBox()
            self.dpi_combo.addItems(["150 (Draft)", "300 (Standard)", "600 (High)"])
            self.dpi_combo.setCurrentIndex(1)
            self.dpi_combo.setMinimumHeight(38)
            self.dpi_combo.setStyleSheet(self.get_combobox_style())
            self.options_layout.addWidget(self.dpi_combo)

            # Page selection
            self.options_layout.addWidget(QLabel("Pages (optional):"))
            self.page_input = QLineEdit()
            self.page_input.setPlaceholderText("e.g., 1,3,5-8")
            self.options_layout.addWidget(self.page_input)

    def on_page_size_changed(self, page_size: str):
        """Handle page size change, show custom dialog if needed."""
        if page_size == "Custom...":
            dialog = CustomPageSizeDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                size = dialog.get_size()
                if size:
                    self.custom_page_size = size
                else:
                    QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers.")
                    self.page_size_combo.setCurrentIndex(0)  # Reset to A4
            else:
                self.page_size_combo.setCurrentIndex(0)  # Reset to A4
        else:
            self.custom_page_size = None

    def get_format_hint_text(self, direction: str) -> str:
        """Build format hint text."""
        if "→ PDF" in direction:
            return "Supports: JPG, PNG, TIFF, BMP, WEBP"
        else:
            return "Supports: PDF"

    def browse_files(self):
        """Open file browser to select files."""
        direction = self.direction_combo.currentText()

        if "→ PDF" in direction:
            # Browsing for images
            file_filter = "Images (*.jpg *.jpeg *.png *.tiff *.tif *.bmp *.webp);;All Files (*)"
        else:
            # Browsing for PDFs
            file_filter = "PDF Files (*.pdf);;All Files (*)"

        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", file_filter)

        if files:
            self.add_files(files)

    def add_files(self, files: List[str]):
        """Add files to the conversion list (additive, doesn't clear existing)."""
        for file_path in files:
            # Basic format check
            ext = Path(file_path).suffix.lower().lstrip(".")
            if not self.config.is_format_allowed(ext):
                QMessageBox.warning(self, "Unsupported Format", f"Format .{ext} is not supported.")
                continue

            # Add to list if not already present
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.workspace.add_thumbnail(file_path)

        # No need to show/hide anything - workspace handles empty state automatically

    def clear_files(self):
        """Clear all files from the list."""
        self.file_list.clear()
        self.workspace.clear_thumbnails()

    def on_thumbnail_deleted(self, index: int):
        """Handle thumbnail deletion by updating file_list."""
        if 0 <= index < len(self.file_list):
            self.file_list.pop(index)

    def on_thumbnails_reordered(self, old_index: int, new_index: int):
        """Handle thumbnail reordering by updating file_list."""
        if 0 <= old_index < len(self.file_list) and 0 <= new_index < len(self.file_list):
            # Reorder file_list to match thumbnail order
            file_path = self.file_list.pop(old_index)
            self.file_list.insert(new_index, file_path)

    def convert_files(self):
        """Start the conversion process."""
        if not self.file_list:
            QMessageBox.warning(self, "No Files", "Please add files to convert.")
            return

        direction = self.direction_combo.currentText()

        if "→ PDF" in direction:
            self.convert_images_to_pdf()
        else:
            self.convert_pdf_to_images()

    def convert_images_to_pdf(self):
        """Convert images to PDF."""
        # Get output file
        output_file, _ = QFileDialog.getSaveFileName(
            self, "Save PDF As", "output.pdf", "PDF Files (*.pdf)"
        )

        if not output_file:
            return

        # Get page size
        page_size_text = self.page_size_combo.currentText()
        if page_size_text == "Custom..." and self.custom_page_size:
            page_size = self.custom_page_size
        else:
            page_size = page_size_text

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.convert_btn.setEnabled(False)

        # Start conversion
        self.conversion_worker = ConversionWorker(
            self.conversion_engine.images_to_pdf, self.file_list, output_file, page_size
        )
        self.conversion_worker.finished.connect(self.on_conversion_finished)
        self.conversion_worker.start()

    def convert_pdf_to_images(self):
        """Convert PDF to images."""
        # Get output directory
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")

        if not output_dir:
            return

        # Get format and DPI
        output_format = self.format_combo.currentText().lower()
        dpi_text = self.dpi_combo.currentText()
        dpi = int(dpi_text.split()[0])

        # Get page selection
        page_numbers = None
        if hasattr(self, "page_input") and self.page_input:
            page_text = self.page_input.text().strip()
            if page_text:
                page_numbers = self.parse_page_selection(page_text)

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.convert_btn.setEnabled(False)

        # Start conversion
        self.conversion_worker = ConversionWorker(
            self.convert_all_pdfs_to_images,
            self.file_list,
            output_dir,
            output_format,
            dpi,
            page_numbers,
        )
        self.conversion_worker.finished.connect(self.on_conversion_finished)
        self.conversion_worker.start()

    def convert_all_pdfs_to_images(self, pdf_files, output_dir, output_format, dpi, page_numbers):
        """Convert multiple PDF files to images."""
        all_output_files = []
        for pdf_file in pdf_files:
            output_files = self.conversion_engine.pdf_to_images(
                pdf_file, output_dir, output_format, dpi, page_numbers
            )
            all_output_files.extend(output_files)
        return all_output_files

    def parse_page_selection(self, selection: str) -> List[int]:
        """Parse page selection string into list of page numbers."""
        page_numbers = []
        parts = selection.split(",")

        for part in parts:
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-")
                    start = int(start.strip())
                    end = int(end.strip())
                    page_numbers.extend(range(start, end + 1))
                except ValueError:
                    pass
            else:
                with contextlib.suppress(ValueError):
                    page_numbers.append(int(part))

        return sorted(set(page_numbers))

    def on_conversion_finished(self, success: bool, message: str):
        """Handle conversion completion with celebration."""
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)

        if success:
            # Show success dialog
            success_dialog = QMessageBox(self)
            success_dialog.setWindowTitle("Success!")
            success_dialog.setIcon(QMessageBox.Icon.NoIcon)

            # Create custom widget with celebration styling
            custom_widget = QWidget()
            custom_layout = QVBoxLayout()
            custom_layout.setSpacing(15)
            custom_layout.setContentsMargins(20, 20, 20, 20)

            # Success icon with gradient background
            icon_container = QWidget()
            icon_container.setFixedSize(80, 80)
            icon_container.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #11998e, stop:1 #38ef7d);
                border-radius: 40px;
            """)
            icon_layout = QVBoxLayout()
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            check_icon = QLabel()
            check_icon.setPixmap(qta.icon("fa5s.check", color="white").pixmap(QSize(40, 40)))
            check_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check_icon.setStyleSheet("background: transparent;")
            icon_layout.addWidget(check_icon)
            icon_container.setLayout(icon_layout)

            icon_container_layout = QHBoxLayout()
            icon_container_layout.addStretch()
            icon_container_layout.addWidget(icon_container)
            icon_container_layout.addStretch()
            custom_layout.addLayout(icon_container_layout)

            # Success message
            title = QLabel("Conversion Complete!")
            title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("color: #2c3e50;")
            custom_layout.addWidget(title)

            msg_label = QLabel(message)
            msg_label.setFont(QFont("Inter", 11))
            msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg_label.setStyleSheet("color: #5a6c7d;")
            msg_label.setWordWrap(True)
            custom_layout.addWidget(msg_label)

            custom_widget.setLayout(custom_layout)

            # Set the custom widget
            success_dialog.setText("")  # Clear default text
            success_dialog.setInformativeText("")
            success_dialog.layout().addWidget(
                custom_widget, 0, 0, 1, success_dialog.layout().columnCount()
            )

            # Style the dialog
            success_dialog.setStyleSheet("""
                QMessageBox {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #f5f7fa, stop:1 #c3cfe2);
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #11998e, stop:1 #38ef7d);
                    color: white;
                    font-weight: bold;
                    font-family: Inter;
                    border-radius: 8px;
                    padding: 8px 20px;
                    min-width: 80px;
                    min-height: 35px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #0e8678, stop:1 #2ed96c);
                }
            """)

            success_dialog.exec()

            # Clear files after successful conversion
            self.clear_files()
        else:
            # Error dialog with modern styling
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Conversion Failed")
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setText(message)
            error_dialog.setStyleSheet("""
                QMessageBox {
                    background-color: #f8f9fa;
                    font-family: Inter;
                }
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 8px 20px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            error_dialog.exec()
