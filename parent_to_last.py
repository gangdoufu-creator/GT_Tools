"""
Parent to Last Selected
Parents all selected objects to the last object in the selection.
"""

import maya.cmds as cmds

def parent_to_last():
    """
    Parents all selected objects to the last object in the selection.
    The last selected object becomes the parent of all other selected objects.
    Works with namespaced and referenced objects.
    """
    # Get selection order - this preserves the exact order you selected
    selection = cmds.ls(selection=True, long=True)
    
    if len(selection) < 2:
        cmds.warning("Please select at least 2 objects. The last selected will be the parent.")
        return
    
    # Last object is the parent
    parent = selection[-1]
    # All others are children to be parented
    children = selection[:-1]
    
    # Get short name (with namespace if present)
    parent_short = parent.split('|')[-1]
    
    print(f"\n=== Parent to Last ===")
    print(f"Parent target: {parent_short}")
    print(f"Full path: {parent}")
    print(f"\nAttempting to parent {len(children)} object(s):")
    
    try:
        # Parent all children to the last selected object
        # Maya handles namespaces automatically when using long names from selection
        parented_objects = cmds.parent(children, parent)
        
        for child in children:
            child_short = child.split('|')[-1]
            print(f"  ✓ {child_short}")
        
        print(f"\nSuccessfully parented {len(children)} object(s) to '{parent_short}'")
        
        # Reselect the newly parented children
        if parented_objects:
            cmds.select(parented_objects, replace=True)
        
    except Exception as e:
        cmds.warning(f"Could not parent objects: {e}")
        print(f"Error details: {e}")
        print("\nDebug info:")
        print(f"  Parent exists: {cmds.objExists(parent)}")
        for i, child in enumerate(children):
            print(f"  Child {i+1} exists: {cmds.objExists(child)} - {child}")

# Run the function
if __name__ == "__main__":
    parent_to_last()
else:
    parent_to_last()
