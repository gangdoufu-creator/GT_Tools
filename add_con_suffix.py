import maya.cmds as cmds

def add_con_suffix_to_selection():
    """
    Adds '_CON' suffix to the end of every selected object's name.
    If the object already ends with '_CON', it won't add another one.
    If the object has multiple '_CON' suffixes, it will clean them up to have only one.
    """
    selection = cmds.ls(selection=True, long=True)
    if not selection:
        cmds.warning("Nothing selected.")
        return []
    renamed = []
    for obj in selection:
        # Get the short name for processing
        original_short_name = obj.split('|')[-1]
        
        # Remove multiple '_CON' suffixes and ensure only one at the end
        # First, remove all '_CON' suffixes
        clean_name = original_short_name
        while clean_name.endswith('_CON'):
            clean_name = clean_name[:-4]  # Remove '_CON' (4 characters)
        
        # Create the target name with exactly one '_CON' suffix
        target_name = clean_name + '_CON'
        
        # Only rename if the name actually needs to change
        if target_name != original_short_name:
            try:
                # Use the full path for renaming to avoid hierarchy issues
                result = cmds.rename(obj, target_name)
                renamed.append(result)
                print(f"Renamed: {original_short_name} -> {target_name}")
            except Exception as e:
                cmds.warning(f"Could not rename {original_short_name}: {e}")
        else:
            print(f"Object {original_short_name} already has correct '_CON' suffix")
    
    if renamed:
        print(f"Renamed objects: {', '.join(renamed)}")
    else:
        print("No objects were renamed.")
    return renamed


add_con_suffix_to_selection()