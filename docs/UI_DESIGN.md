# ZImage - UI Design Specification

## 1. Overview
ZImage maintains its clean, minimal interface while integrating enhanced features through smart UI component reuse and extension.

## 2. Layout Structure

### 2.1 Main Window Layout
```
+----------------------------------------+
| Menu Bar                               |
|----------------------------------------|
| Tool Bar                               |
|----------------------------------------|
| Output Directory Selection             |
|----------------------------------------|
| +------------------+------------------+ |
| |   Left Panel     |   Right Panel   | |
| |   (Controls)     |   (Preview)     | |
| |                  |                 | |
| +------------------+------------------+ |
| Status Bar                             |
+----------------------------------------+
```

### 2.2 Component Details

#### Menu Bar
- File
  - New Queue
  - Open Images
  - Recent Files (New) ▶
    - Last 10 files
    - Clear Recent
  - Save Queue
  - Load Queue
  - Favorites (New) ▶
    - Favorite Folders
    - Add Current Folder
  - Exit

- Edit
  - Undo (New)
  - Redo (New)
  - Presets (New) ▶
    - Save Current Queue
    - Load Preset
    - Manage Presets
  - Preferences (New) ▶
    - Theme Settings
    - Performance Settings
    - Cache Settings

- View
  - Theme (New) ▶
    - Light Mode
    - Dark Mode
    - System Default
  - Preview Mode (New) ▶
    - Single Image
    - Side by Side
    - Before/After
  - Status Bar
  - Tool Bar

- Help
  - Documentation
  - About
  - Check Updates

#### Tool Bar
```
[Open] [Save] | [Add Files] [Clear] | [Theme] | [Start] [Cancel]
```

#### Left Panel (Controls)
1. **Drag & Drop Area**
   - File drop zone
   - Preview thumbnail (New)
   - File count indicator

2. **Action Controls**
   - Available Actions List
   - Action Queue
   - Queue Controls
   - Preset Controls (New)

3. **Action Parameters**
   - Dynamic options per action
   - Parameter presets (New)
   - Quick settings (New)

#### Right Panel (Preview)
1. **Preview Area**
   - Image preview
   - Before/After slider (New)
   - Zoom controls
   - Pan controls

2. **Image Information (New)**
   ```
   +--------------------------------+
   | Image Details                  |
   | - Dimensions: 1920 x 1080     |
   | - Size: 2.4 MB                |
   | - Format: PNG                 |
   | - Color Mode: RGB             |
   +--------------------------------+
   ```

#### Status Bar
```
[Theme] | Files: 5 | Queue: 3 actions | Cache: 80% | Memory: 420MB | Ready
```

## 3. Feature Integration

### 3.1 Theme Management
- Theme toggle in toolbar
- Color scheme applied to existing components
- No layout changes required

### 3.2 Enhanced Processing
1. **Preview System**
   - Integrated into existing preview area
   - Split view option
   - Real-time preview toggle

2. **Progress Tracking**
   - Enhanced existing progress bar
   - Per-file progress
   - Action progress
   - Time estimation

3. **File Information**
   - Added to status bar
   - Detailed view in right panel
   - EXIF data display

### 3.3 File Management
1. **Recent Files**
   - Added to File menu
   - Quick access list
   - Clear history option

2. **Favorites**
   - Added to File menu
   - Favorite folders management
   - Quick access paths

3. **Presets**
   - Added to Edit menu
   - Preset management dialog
   - Quick load/save

## 4. Component States

### 4.1 Light Theme
```css
Background: #FFFFFF
Text: #000000
Accent: #007AFF
Secondary: #757575
Border: #E0E0E0
```

### 4.2 Dark Theme
```css
Background: #353535
Text: #FFFFFF
Accent: #2A82DA
Secondary: #666666
Border: #484848
```

## 5. Interaction Patterns

### 5.1 Drag and Drop
- File drop highlights
- Invalid file feedback
- Batch file acceptance
- Directory drop support

### 5.2 Action Queue
- Drag to reorder
- Quick remove
- Batch enable/disable
- Preset save/load

### 5.3 Preview
- Mouse wheel zoom
- Pan with middle mouse
- Double click reset
- Side-by-side slider

## 6. Responsive Behavior

### 6.1 Window Resizing
- Minimum size: 800x600
- Dynamic preview scaling
- Collapsible panels
- Scrollable sections

### 6.2 Performance Feedback
- Progress indication
- Processing status
- Cache status
- Memory usage

## 7. Accessibility

### 7.1 Keyboard Navigation
- Full keyboard control
- Shortcut keys
- Focus indicators
- Tab order

### 7.2 Visual Assistance
- High contrast support
- Screen reader compatibility
- Scalable UI
- Clear feedback

## 8. Error Handling

### 8.1 User Feedback
- Error notifications
- Warning dialogs
- Progress updates
- Success confirmation

### 8.2 Recovery Actions
- Cancel operation
- Retry failed actions
- Restore defaults
- Clear queue

## 9. Implementation Notes

### 9.1 Code Structure
```python
class MainWindow(QMainWindow):
    def init_ui(self):
        # Main layout remains unchanged
        self.init_menu_bar()
        self.init_tool_bar()
        self.init_main_layout()
        self.init_status_bar()
        
    def enhance_features(self):
        # Add new features to existing components
        self.add_theme_support()
        self.enhance_preview()
        self.add_file_management()
        self.add_performance_monitoring()
```

### 9.2 Performance Considerations
- Lazy loading of previews
- Cache management
- Background processing
- Memory optimization 