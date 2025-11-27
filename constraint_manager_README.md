# Constraint Manager

A professional-grade Maya tool for managing constraints in production environments.

## Features

### Selection Tools
- **Select Constraining Objects** - Finds and selects all driver/source objects that constrain your selection
- **Select Constraint Nodes** - Selects all constraint nodes connected to your selected objects

### Constraint Deletion
- **Delete Constraints on Selection** - Removes all constraints from selected objects
- **Delete Selected Constraint Nodes** - Deletes currently selected constraint nodes

### Professional Features
- ✅ Full undo support
- ✅ Safe deletion (skips referenced and locked constraints)
- ✅ In-viewport feedback messages
- ✅ Comprehensive error handling and warnings
- ✅ Long name handling for namespace safety
- ✅ Maintains selection after operations

## Usage

### In Maya Script Editor (Python):

```python
import select_constraint_sources
select_constraint_sources.launch_constraint_manager_ui()
```

### Add to Shelf:

1. Open Maya Script Editor
2. Create a new Python tab
3. Paste the following code:

```python
import select_constraint_sources
select_constraint_sources.launch_constraint_manager_ui()
```

4. Middle-mouse drag the code to your shelf

### Typical Workflows

#### Workflow 1: Quick Constraint Cleanup
1. Select constrained objects
2. Click **"Delete Constraints on Selection"**
3. Done! (Press Ctrl+Z if needed to undo)

#### Workflow 2: Selective Constraint Deletion
1. Select constrained objects
2. Click **"Select Constraint Nodes"** to see what constraints exist
3. In the outliner, deselect any constraints you want to keep
4. Click **"Delete Selected Constraint Nodes"**

#### Workflow 3: Find Constraint Sources
1. Select constrained objects
2. Click **"Select Constraining Objects"**
3. Now you have all the driver objects selected for inspection or further manipulation

## Technical Details

### Supported Constraint Types
- Point Constraint
- Orient Constraint
- Parent Constraint
- Scale Constraint
- Aim Constraint
- Pole Vector Constraint
- Geometry Constraint
- Normal Constraint
- Tangent Constraint

### Safety Features
- **Referenced Nodes**: Skips deletion of referenced constraints (with warning)
- **Locked Nodes**: Skips deletion of locked constraints (with warning)
- **Undo Support**: All deletion operations are wrapped in undo chunks
- **Error Recovery**: Continues operation even if individual constraints fail to delete

### Performance Considerations
- Uses long names throughout to avoid namespace conflicts
- Set-based filtering for efficient duplicate removal
- Single-pass constraint collection for large selections

## Code Quality

This tool follows VFX studio best practices:
- Comprehensive docstrings on all functions
- Clear separation of concerns (core functions vs UI)
- Defensive programming with existence checks
- Professional error handling and user feedback
- Legacy function support for backwards compatibility

## Backwards Compatibility

The original `launch_constraint_source_ui()` function is still available and redirects to the new UI.

---

**Author**: Professional Pipeline Tools  
**Version**: 2.0  
**Maya Version**: 2020+
