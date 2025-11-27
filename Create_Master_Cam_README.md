# Master Camera Builder

## Overview
The Master Camera Builder is a Maya tool that creates a single "master" camera that sequences through multiple shot cameras. It automatically matches the position, rotation, and attributes (focal length, film back, etc.) of each shot camera during its specified frame range.

## Purpose
When working with multiple camera shots in Maya, you often need a single camera that transitions between different shot cameras at specific frames. This tool automates the process by:
- Baking the transform animation from each shot camera into the master camera
- Copying camera-specific attributes (focal length, film aperture, depth of field, etc.)
- Maintaining proper animation without interpolation between shots

## Key Features

### 1. **Automatic Frame Range Detection**
- Scans camera animation keyframes to automatically determine shot ranges
- Excludes handle frames from the start and end of animation
- Works with locked camera attributes

### 2. **Handle Frames**
- Specify how many frames to exclude from the beginning and end of each shot
- Example: Camera animated from frame 1000-1100, with 10 frame handles = shot range 1010-1090

### 3. **Batch Camera Addition**
- Select multiple cameras and add them all at once
- Maintains selection order in the shot list
- Auto-detects frame ranges for each camera

### 4. **Save/Load Shot Lists**
- Save your camera sequence to a JSON file
- Load previously saved sequences
- Share shot lists between scenes or team members

### 5. **Attribute Copying**
- Copies selected camera attributes (focal length, film aperture, etc.)
- Animated attributes: Copies all keyframes
- Static attributes: Holds constant value with no interpolation

### 6. **Optimized Performance**
- Single bake pass per camera
- Viewport refresh suspension during processing
- No unnecessary simulation calculations

## How to Use

### Initial Setup
1. **Run the script** in Maya:
   ```python
   import Create_Master_Cam
   # UI will open automatically
   ```

2. **Select or create a master camera**:
   - Click the "Pick" button next to "Select Master Camera"
   - Select your master camera in the scene
   - This is the camera that will receive all the baked animation

### Adding Cameras to the Shot List

**Method 1: Auto-Detect Frame Ranges (Recommended)**
1. Set the **Handle Frames** value (default: 10)
   - This is how many frames to exclude from start/end of animation
2. Select one or more shot cameras in your scene (in the order you want them)
3. Click **"Add Camera"** (green button)
4. The tool will automatically:
   - Find the first and last keyframes on the camera
   - Calculate: Start = First keyframe + Handles
   - Calculate: End = Last keyframe - Handles
   - Add the camera to the list

**Method 2: Manual Frame Ranges**
1. Select a camera
2. Manually enter **Start** and **End** frames
3. Click **"Add Camera"**
4. The manual values will be used

### Editing Frame Ranges
1. **Select a shot** in the list (single-click)
2. **Change the Start/End frame values**
3. Click **"Edit Time Range"** (purple button)
4. The selected shot's range will be updated

### Removing Cameras
1. Select one or more shots in the list
2. Click **"Remove Selected"**

### Save/Load Shot Lists

**To Save:**
1. Set up your camera list with all shots and frame ranges
2. Click **"Save Shot List"**
3. Choose a location and filename in the file dialog
4. File is saved as JSON (human-readable format)

**To Load:**
1. Click **"Load Shot List"**
2. Select a previously saved JSON file
3. The shot list will be populated automatically

### Selecting Camera Attributes to Copy
The tool can copy various camera attributes from each shot camera to the master:
- **Focal Length** - Lens focal length
- **Film Aperture** - Horizontal/vertical film back size
- **Film Fit** - How the film gate fits
- **Film Translate** - Film back offset
- **Focus Distance** - Focus distance for DOF
- **F-Stop** - Aperture f-stop
- **Depth of Field** - DOF enable/disable
- **Clip Planes** - Near and far clipping planes

By default, all attributes are selected. You can:
- **Deselect attributes** you don't want to copy
- **Multi-select** specific attributes using Ctrl+Click

### Building the Master Camera
1. Ensure your master camera is selected
2. Verify all shots are in the list with correct frame ranges
3. Select which camera attributes to copy
4. Click **"Build Master Camera"** (large green button at bottom)

**What happens:**
- Any existing animation on the master camera is cleared
- For each shot in order:
  - Creates a parent constraint from shot camera to master camera
  - Bakes the transform animation for that frame range
  - Deletes the constraint
  - Copies camera attributes (animated or static)
- Progress is printed in the Script Editor
- Success message appears when complete

## Workflow Example

### Scenario: 5 Shot Sequence
You have 5 cameras: `shot_01_cam` through `shot_05_cam`, each animated with handles.

1. **Create a master camera** (or select an existing one)
2. **Set Handle Frames to 10**
3. **Select all 5 cameras in order** (shot_01 → shot_05)
4. **Click "Add Camera"**
   - Tool auto-detects frame ranges for all 5 cameras
   - Example results:
     - shot_01_cam | 1010-1090
     - shot_02_cam | 1110-1190
     - shot_03_cam | 1210-1290
     - shot_04_cam | 1310-1390
     - shot_05_cam | 1410-1490

5. **Save the shot list** (optional but recommended)
   - Click "Save Shot List"
   - Save as `my_sequence.json`

6. **Click "Build Master Camera"**
   - Master camera now follows each shot camera during its range
   - Camera attributes match each shot
   - No interpolation between different focal lengths or other attributes

## Tips & Best Practices

### Frame Ranges
- **Handles are common in animation** - typically 8-12 frames
- **Non-overlapping ranges** work best (gaps between shots are fine)
- **Overlapping ranges** will cause the later shot to override the earlier one

### Camera Attributes
- **Enable "Depth of Field"** in the attributes list if your shots use DOF
- **Disable attributes** that are rigged or controlled elsewhere
- **Static values** (like focal length with no animation) will hold constant without interpolation

### Performance
- The tool automatically suspends viewport refresh during baking
- Larger frame ranges take longer to process
- Processing time: ~1-2 seconds per camera on typical hardware

### Saving/Loading
- **JSON files are human-readable** - you can edit them in a text editor
- **Save after major changes** to avoid re-entering data
- **Share JSON files** with team members working on the same sequence

### Troubleshooting
- **"No animation found"** warning: Camera has no keyframes on transform attributes
  - Check if the camera is actually animated
  - Verify attributes aren't connected to rigs outside the camera hierarchy
- **Invalid range warning**: Handle frames are too large for the animation range
  - Reduce the handle frames value
  - Check the actual keyframe range of your camera

## File Format (JSON)

Example saved shot list:
```json
[
    {
        "camera": "shot_01_cam",
        "start": 1010,
        "end": 1090
    },
    {
        "camera": "shot_02_cam",
        "start": 1110,
        "end": 1190
    }
]
```

## Technical Notes

### Animation Curve Detection
- Works with **locked attributes** (uses animation curve connections)
- Checks: translateX, translateY, translateZ, rotateX, rotateY, rotateZ
- Finds first and last keyframes across all checked attributes

### Baking Settings
- **simulation=False** - No physics simulation overhead
- **preserveOutsideKeys=True** - Keeps animation from previous shots
- **minimizeRotation=True** - Prevents rotation flipping
- **sparseAnimCurveBake=False** - Creates keys on every frame

### Attribute Copying
- **Animated attributes**: All keyframes copied within the frame range
- **Static attributes**: Single keyframe with stepped tangent (holds value)
- Keyframes set at the start of each shot's range

## Version History
- **v2.0** - Added auto frame range detection, save/load, handle frames support
- **v1.0** - Initial release with manual frame ranges

## Support
For issues or feature requests, contact the pipeline team or check the GT_Tools repository.
