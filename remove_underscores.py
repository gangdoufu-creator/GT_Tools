"""
Remove Underscores from Selection
Removes underscores and everything after them from selected objects and their entire hierarchies.
"""

import maya.cmds as cmds


def remove_underscores_from_hierarchy(root_nodes=None, dry_run=False, remove_namespace=False):
    """
    Remove all underscores from node names in the hierarchy.
    
    Args:
        root_nodes (list): List of root nodes to process. If None, uses current selection.
        dry_run (bool): If True, only shows what would be renamed without actually renaming.
        remove_namespace (bool): If True, also removes the namespace prefix.
    
    Returns:
        int: Number of nodes renamed
    """
    if root_nodes is None:
        root_nodes = cmds.ls(selection=True, long=True)
    
    if not root_nodes:
        cmds.warning("No objects selected.")
        return 0
    
    # Get all descendants of the selected nodes
    all_nodes = []
    for root in root_nodes:
        all_nodes.append(root)
        # Get all children recursively
        descendants = cmds.listRelatives(root, allDescendents=True, fullPath=True) or []
        all_nodes.extend(descendants)
    
    # Remove duplicates and sort by depth (deepest first to avoid parent renaming issues)
    all_nodes = list(set(all_nodes))
    all_nodes.sort(key=lambda x: x.count('|'), reverse=True)
    
    print("\n" + "=" * 60)
    if dry_run:
        print("DRY RUN MODE - No nodes will be renamed")
    print("=" * 60)
    print(f"Processing {len(all_nodes)} nodes...")
    print("-" * 60)
    
    renamed_count = 0
    skipped_count = 0
    
    for node in all_nodes:
        # Get the short name (without path)
        short_name = node.split('|')[-1]
        
        # Remove namespace prefix to get just the node name
        if ':' in short_name:
            namespace_prefix = ':'.join(short_name.split(':')[:-1]) + ':'
            node_name = short_name.split(':')[-1]
        else:
            namespace_prefix = ''
            node_name = short_name
        
        # Check if there are underscores to remove
        if '_' not in node_name:
            skipped_count += 1
            continue
        
        # Remove underscore and everything after it (or before if remove_namespace is True)
        if remove_namespace:
            # Remove everything before and including the underscore
            new_node_name = '_'.join(node_name.split('_')[1:])
            # Don't use namespace prefix when removing prefix
            new_full_name = new_node_name if new_node_name else node_name
        else:
            # Remove underscore and everything after it
            new_node_name = node_name.split('_')[0]
            new_full_name = namespace_prefix + new_node_name
        
        print(f"  {short_name} -> {new_full_name}")
        
        if not dry_run:
            try:
                cmds.rename(node, new_full_name)
                renamed_count += 1
            except Exception as e:
                print(f"    ✗ Error renaming: {e}")
        else:
            renamed_count += 1
    
    print("\n" + "=" * 60)
    if dry_run:
        print(f"WOULD RENAME {renamed_count} nodes")
        print(f"Would skip {skipped_count} nodes (no underscores)")
    else:
        print(f"✓ Successfully renamed {renamed_count} nodes")
        print(f"Skipped {skipped_count} nodes (no underscores)")
    print("=" * 60)
    
    return renamed_count


def remove_underscores_ui():
    """Create a UI for removing underscores from selection."""
    window_name = "removeUnderscoresWindow"
    
    # Delete existing window if it exists
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    # Create window
    window = cmds.window(window_name, title="Remove Underscores", widthHeight=(400, 200))
    
    main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=10)
    
    cmds.separator(height=10, style="none")
    cmds.text(label="Remove Underscores from Selection", font="boldLabelFont", align="center")
    cmds.separator(height=10, style="none")
    
    # Instructions
    cmds.text(label="Select root object(s) to process", align="center")
    cmds.text(label="All objects in hierarchy will be renamed", 
              font="smallPlainLabelFont", align="center")
    cmds.separator(height=10, style="none")
    
    # Example
    cmds.frameLayout(label="Example", collapsable=False, borderStyle="etchedIn")
    cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
    cmds.text(label="Remove After:  MyObject_Name_123 -> MyObject", align="left", font="smallPlainLabelFont")
    cmds.text(label="Remove Before: MyObject_Name_123 -> Name_123", align="left", font="smallPlainLabelFont")
    cmds.setParent('..')
    cmds.setParent('..')
    
    cmds.separator(height=10, style="none")
    
    # Options
    remove_prefix_check = cmds.checkBox(label="Remove Before Underscore (instead of after)", value=False)
    
    cmds.separator(height=10, style="none")
    
    # Buttons
    def run_preview(*args):
        remove_prefix = cmds.checkBox(remove_prefix_check, query=True, value=True)
        remove_underscores_from_hierarchy(dry_run=True, remove_namespace=remove_prefix)
    
    def run_rename(*args):
        remove_prefix = cmds.checkBox(remove_prefix_check, query=True, value=True)
        # Confirmation dialog
        result = cmds.confirmDialog(
            title='Confirm Rename',
            message='Are you sure you want to remove underscores from all selected objects and their hierarchies?\n\nThis action can be undone with Ctrl+Z.',
            button=['Rename', 'Cancel'],
            defaultButton='Rename',
            cancelButton='Cancel',
            dismissString='Cancel'
        )
        
        if result == 'Rename':
            remove_underscores_from_hierarchy(dry_run=False, remove_namespace=remove_prefix)
    
    cmds.button(label="Preview (Dry Run)", 
                command=run_preview,
                height=35,
                backgroundColor=[0.4, 0.4, 0.7])
    
    cmds.separator(height=5, style="none")
    
    cmds.button(label="REMOVE UNDERSCORES", 
                command=run_rename,
                height=40,
                backgroundColor=[0.3, 0.6, 0.3])
    
    cmds.separator(height=10, style="none")
    cmds.text(label="Tip: Use 'Preview' first to see what will be renamed!", 
              font="smallPlainLabelFont", align="center")
    
    cmds.showWindow(window)


# Quick execute function
def remove_underscores_from_selection(dry_run=True):
    """Quick function to remove underscores from current selection."""
    return remove_underscores_from_hierarchy(dry_run=dry_run)


# Execute when script is run directly
if __name__ == "__main__":
    remove_underscores_ui()
