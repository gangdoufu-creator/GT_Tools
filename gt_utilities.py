
import maya.cmds as cmds

def get_selection_name():
    """Returns the name of the currently selected object."""
    selection = cmds.ls(selection=True)
    if len(selection) == 1:
        return selection[0]
        print(selection[0])
    else:
        raise ValueError("Please select exactly one object.")


def remove_namespace(char_name):
    """
    Removes the namespace from the given character name.
    """
    # Split the character name into namespace and name components
    parts = char_name.split(':')
    
    if len(parts) > 1:
        # Remove the namespace from the character name
        char_name = parts[-1]
        
    return char_name
    
    
def get_namespace(char_name):
    """
    Returns the namespace from the given character name.
    """
    # Split the character name into namespace and name components
    parts = char_name.split(':')
    
    if len(parts) > 1:
        # Join the namespace components into a string
        namespace = ':'.join(parts[:-1])
    else:
        # No namespace present
        namespace = ''
        
    return namespace
    
        

def bake_controls(controls_to_bake):  
   

    # Get a list of the controls to be baked
    controls_to_bake = sorted(cmds.sets( controls_to_bake, q=True ), key=str.lower)
   
    # Select all objects in the list
    cmds.select(controls_to_bake)
   
    # Set the start and end frames for baking
    start_frame = cmds.playbackOptions(q=True, min=True)
    end_frame = cmds.playbackOptions(q=True, max=True)
   
    # Bake the animation on each selected object
    cmds.bakeResults(simulation=True, t=(start_frame, end_frame))
   
    # Deselect all objects
    cmds.select(clear=True)