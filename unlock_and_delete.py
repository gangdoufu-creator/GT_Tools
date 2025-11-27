"""
Unlock and Delete Tool
Unlocks all locked/read-only children of selected nodes and deletes them.

Usage:
1. Select the node(s) you want to delete
2. Run: unlock_and_delete()
"""

import maya.cmds as cmds


def unlock_attributes(node):
    """Unlock all attributes on a node."""
    try:
        # Get all attributes
        attrs = cmds.listAttr(node, locked=True) or []
        
        for attr in attrs:
            try:
                cmds.setAttr(f"{node}.{attr}", lock=False)
            except:
                pass  # Some attributes can't be unlocked, skip them
    except:
        pass


def unlock_hierarchy(node):
    """Recursively unlock all nodes in hierarchy."""
    if not cmds.objExists(node):
        return
    
    # Unlock this node
    unlock_attributes(node)
    
    # Get all children recursively
    children = cmds.listRelatives(node, allDescendents=True, fullPath=True) or []
    
    for child in children:
        unlock_attributes(child)


def unlock_and_delete(nodes=None):
    """
    Unlock all children and delete the specified nodes.
    
    Args:
        nodes: List of node names. If None, uses current selection.
    """
    if nodes is None:
        nodes = cmds.ls(selection=True, long=True)
    
    if not nodes:
        cmds.warning("No nodes selected or specified.")
        return
    
    if isinstance(nodes, str):
        nodes = [nodes]
    
    deleted = []
    failed = []
    
    for node in nodes:
        if not cmds.objExists(node):
            print(f"Node doesn't exist: {node}")
            continue
        
        try:
            print(f"\nProcessing: {node}")
            
            # Check if it's a referenced node
            try:
                is_referenced = cmds.referenceQuery(node, isNodeReferenced=True)
            except:
                is_referenced = False
            
            if is_referenced:
                print(f"  Node is referenced. Attempting to remove reference...")
                try:
                    ref_node = cmds.referenceQuery(node, referenceNode=True)
                    ref_file = cmds.referenceQuery(node, filename=True)
                    print(f"  Reference: {ref_node}")
                    print(f"  File: {ref_file}")
                    
                    # Try to remove the reference
                    cmds.file(ref_file, removeReference=True)
                    deleted.append(node)
                    print(f"✓ Removed reference for: {node}")
                    continue
                except Exception as e:
                    print(f"  Could not remove reference: {e}")
            
            # Get all descendents first
            all_nodes = cmds.listRelatives(node, allDescendents=True, fullPath=True) or []
            all_nodes.append(node)
            
            print(f"  Unlocking {len(all_nodes)} nodes...")
            
            # Unlock everything including node lock
            for n in all_nodes:
                if cmds.objExists(n):
                    try:
                        cmds.lockNode(n, lock=False)
                    except:
                        pass
                    unlock_attributes(n)
            
            # Try to delete
            print(f"  Attempting delete...")
            cmds.delete(node)
            deleted.append(node)
            print(f"✓ Deleted: {node}")
            
        except Exception as e:
            failed.append(node)
            print(f"✗ Failed to delete {node}: {e}")
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"Deleted: {len(deleted)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed nodes: {failed}")
    
    return deleted


# Quick function to delete a specific node by name
def delete_node(node_name):
    """Delete a specific node by name."""
    unlock_and_delete([node_name])


if __name__ == "__main__":
    # Run on selection
    unlock_and_delete()
