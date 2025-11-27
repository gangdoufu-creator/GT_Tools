"""
Delete Nodes by Name Pattern
A tool to delete multiple nodes based on name patterns (substrings).
Excludes joints by default to prevent rig breakage.
"""

import maya.cmds as cmds
import json
import os


def delete_nodes_by_patterns(patterns, exclude_joints=True, dry_run=False):
    """
    Delete nodes whose names contain any of the specified patterns.
    
    Args:
        patterns (list): List of string patterns to search for in node names
        exclude_joints (bool): If True, skips joint nodes (default: True)
        dry_run (bool): If True, only prints what would be deleted without actually deleting (default: False)
    
    Returns:
        int: Number of nodes deleted (or would be deleted in dry_run mode)
    """
    if not patterns:
        print("No patterns provided.")
        return 0
    
    all_nodes_to_delete = []
    
    print("\n" + "=" * 60)
    if dry_run:
        print("DRY RUN MODE - No nodes will be deleted")
    print("=" * 60)
    print(f"Searching for patterns: {patterns}")
    print(f"Exclude joints: {exclude_joints}")
    print("-" * 60)
    
    # Get ALL nodes in the scene first, then filter by pattern
    # This is more reliable than wildcard search with namespaces
    # Use dagObjects=True to get all DAG nodes including deeply nested ones
    all_scene_nodes = cmds.ls(long=True, dagObjects=True)
    # Also get dependency nodes (non-DAG nodes like shaders, etc.)
    all_scene_nodes += cmds.ls(long=True, dependencyNodes=True)
    # Remove duplicates
    all_scene_nodes = list(set(all_scene_nodes))
    
    print(f"Total nodes in scene: {len(all_scene_nodes)}")
    
    # Search for each pattern
    for pattern in patterns:
        matching_nodes = []
        
        print(f"\nSearching for pattern: '{pattern}'")
        
        # Filter nodes that contain the pattern (case-insensitive)
        for node in all_scene_nodes:
            # Check both the full path and the short name
            short_name = node.split('|')[-1]
            # Also check without namespace
            name_without_ns = short_name.split(':')[-1] if ':' in short_name else short_name
            
            # Debug: Print first few matches
            if pattern.lower() in name_without_ns.lower():
                matching_nodes.append(node)
                if len(matching_nodes) <= 5:  # Show first 5 matches as we find them
                    print(f"  Found: {short_name}")
            elif pattern.lower() in short_name.lower():
                matching_nodes.append(node)
                if len(matching_nodes) <= 5:
                    print(f"  Found: {short_name}")
            elif pattern.lower() in node.lower():
                matching_nodes.append(node)
                if len(matching_nodes) <= 5:
                    print(f"  Found: {short_name}")
        
        if matching_nodes:
            print(f"\nFound {len(matching_nodes)} nodes matching pattern '{pattern}':")
            for node in matching_nodes:
                short_name = node.split('|')[-1]  # Get short name for display
                try:
                    node_type = cmds.nodeType(node)
                    print(f"  - {short_name} [{node_type}]")
                except:
                    print(f"  - {short_name} [unknown type]")
            
            all_nodes_to_delete.extend(matching_nodes)
        else:
            print(f"\nNo nodes found matching pattern '{pattern}'")
    
    # Remove duplicates (a node might match multiple patterns)
    all_nodes_to_delete = list(set(all_nodes_to_delete))
    
    if not all_nodes_to_delete:
        print("\n" + "=" * 60)
        print("No nodes found matching any patterns.")
        print("=" * 60)
        return 0
    
    # Filter out joints if requested
    if exclude_joints:
        original_count = len(all_nodes_to_delete)
        all_nodes_to_delete = [n for n in all_nodes_to_delete if cmds.nodeType(n) != 'joint']
        filtered_count = original_count - len(all_nodes_to_delete)
        if filtered_count > 0:
            print(f"\n⚠ Excluded {filtered_count} joint(s) from deletion")
    
    if not all_nodes_to_delete:
        print("\n" + "=" * 60)
        print("No non-joint nodes to delete.")
        print("=" * 60)
        return 0
    
    # Print summary
    print("\n" + "=" * 60)
    if dry_run:
        print(f"WOULD DELETE {len(all_nodes_to_delete)} nodes:")
    else:
        print(f"DELETING {len(all_nodes_to_delete)} nodes:")
    print("=" * 60)
    
    for node in all_nodes_to_delete:
        short_name = node.split('|')[-1]
        node_type = cmds.nodeType(node)
        print(f"  [{node_type}] {short_name}")
    
    # Delete nodes
    if not dry_run:
        cmds.undoInfo(openChunk=True)
        try:
            cmds.delete(all_nodes_to_delete)
            print("\n" + "=" * 60)
            print(f"✓ Successfully deleted {len(all_nodes_to_delete)} nodes.")
            print("=" * 60)
        except Exception as e:
            print(f"\n✗ Error during deletion: {e}")
            return 0
        finally:
            cmds.undoInfo(closeChunk=True)
    else:
        print("\n" + "=" * 60)
        print("DRY RUN COMPLETE - No nodes were deleted")
        print("Run with dry_run=False to actually delete these nodes")
        print("=" * 60)
    
    return len(all_nodes_to_delete)


def save_patterns_to_file(patterns, filepath):
    """
    Save patterns list to a JSON file.
    
    Args:
        patterns (list): List of pattern strings to save
        filepath (str): Full path to the JSON file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data = {
            "patterns": patterns,
            "description": "Delete Nodes by Name - Pattern List"
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        
        print(f"✓ Saved {len(patterns)} patterns to: {filepath}")
        return True
    except Exception as e:
        print(f"✗ Error saving patterns: {e}")
        return False


def load_patterns_from_file(filepath):
    """
    Load patterns list from a JSON file.
    
    Args:
        filepath (str): Full path to the JSON file
    
    Returns:
        list: List of patterns, or empty list if error
    """
    try:
        if not os.path.exists(filepath):
            print(f"✗ File not found: {filepath}")
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        patterns = data.get("patterns", [])
        print(f"✓ Loaded {len(patterns)} patterns from: {filepath}")
        return patterns
    except Exception as e:
        print(f"✗ Error loading patterns: {e}")
        return []


def delete_nodes_ui():
    """Create a UI for deleting nodes by name patterns."""
    window_name = "deleteNodesByNameWindow"
    
    # Delete existing window if it exists
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    # Create window
    window = cmds.window(window_name, title="Delete Nodes by Name", widthHeight=(450, 350))
    
    main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    
    cmds.separator(height=10, style="none")
    cmds.text(label="Delete Nodes by Name Pattern", font="boldLabelFont", align="center")
    cmds.separator(height=10, style="none")
    
    # Instructions
    cmds.text(label="Enter patterns to search for (one per line):", align="left")
    cmds.text(label="Example: 'FKOffsettailFin', 'tempNode', 'old_', etc.", 
              font="smallPlainLabelFont", align="left")
    cmds.separator(height=5, style="none")
    
    # Text field for patterns
    patterns_field = cmds.scrollField(height=100, wordWrap=False, 
                                      text="FKOffsettailFin\n")
    
    cmds.separator(height=5, style="none")
    
    # Save/Load buttons
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(220, 220), columnAlign=[(1, "center"), (2, "center")])
    
    def save_patterns(*args):
        patterns_text = cmds.scrollField(patterns_field, query=True, text=True)
        patterns = [p.strip() for p in patterns_text.split('\n') if p.strip()]
        
        if not patterns:
            cmds.warning("No patterns to save.")
            return
        
        # File dialog to choose save location
        result = cmds.fileDialog2(
            fileMode=0,  # Save file
            caption="Save Pattern List",
            fileFilter="JSON Files (*.json)",
            defaultExtension="json"
        )
        
        if result:
            filepath = result[0]
            if save_patterns_to_file(patterns, filepath):
                cmds.confirmDialog(
                    title='Success',
                    message=f'Saved {len(patterns)} patterns to:\n{filepath}',
                    button=['OK'],
                    defaultButton='OK'
                )
    
    def load_patterns(*args):
        # File dialog to choose file to load
        result = cmds.fileDialog2(
            fileMode=1,  # Open file
            caption="Load Pattern List",
            fileFilter="JSON Files (*.json)"
        )
        
        if result:
            filepath = result[0]
            patterns = load_patterns_from_file(filepath)
            
            if patterns:
                # Update the text field with loaded patterns
                patterns_text = '\n'.join(patterns)
                cmds.scrollField(patterns_field, edit=True, text=patterns_text + '\n')
                cmds.confirmDialog(
                    title='Success',
                    message=f'Loaded {len(patterns)} patterns from:\n{filepath}',
                    button=['OK'],
                    defaultButton='OK'
                )
    
    cmds.button(label="Save List to File", 
                command=save_patterns,
                backgroundColor=[0.3, 0.6, 0.3])
    cmds.button(label="Load List from File", 
                command=load_patterns,
                backgroundColor=[0.3, 0.5, 0.7])
    cmds.setParent("..")
    
    cmds.separator(height=10, style="none")
    
    # Options
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 200))
    exclude_joints_check = cmds.checkBox(label="Exclude Joints", value=True)
    cmds.text(label="")  # Spacer
    cmds.setParent("..")
    
    cmds.separator(height=10, style="none")
    
    # Buttons
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(220, 220), columnAlign=[(1, "center"), (2, "center")])
    
    def run_dry_run(*args):
        patterns_text = cmds.scrollField(patterns_field, query=True, text=True)
        patterns = [p.strip() for p in patterns_text.split('\n') if p.strip()]
        exclude_joints = cmds.checkBox(exclude_joints_check, query=True, value=True)
        delete_nodes_by_patterns(patterns, exclude_joints=exclude_joints, dry_run=True)
    
    def run_delete(*args):
        patterns_text = cmds.scrollField(patterns_field, query=True, text=True)
        patterns = [p.strip() for p in patterns_text.split('\n') if p.strip()]
        exclude_joints = cmds.checkBox(exclude_joints_check, query=True, value=True)
        
        # Confirmation dialog
        result = cmds.confirmDialog(
            title='Confirm Deletion',
            message='Are you sure you want to delete these nodes?\nThis action can be undone with Ctrl+Z.',
            button=['Delete', 'Cancel'],
            defaultButton='Cancel',
            cancelButton='Cancel',
            dismissString='Cancel'
        )
        
        if result == 'Delete':
            delete_nodes_by_patterns(patterns, exclude_joints=exclude_joints, dry_run=False)
    
    cmds.button(label="Preview (Dry Run)", 
                command=run_dry_run,
                backgroundColor=[0.4, 0.4, 0.7])
    cmds.button(label="DELETE NODES", 
                command=run_delete,
                backgroundColor=[0.7, 0.3, 0.3])
    cmds.setParent("..")
    
    cmds.separator(height=10, style="none")
    cmds.text(label="Tip: Use 'Preview' first to see what will be deleted!", 
              font="smallPlainLabelFont", align="center")
    
    cmds.showWindow(window)


# Quick execute functions
def delete_fin_nodes(dry_run=True):
    """Quick function to delete nodes containing 'FKOffsettailFin'."""
    return delete_nodes_by_patterns(['FKOffsettailFin'], exclude_joints=True, dry_run=dry_run)


# Execute when script is run directly
if __name__ == "__main__":
    delete_nodes_ui()
