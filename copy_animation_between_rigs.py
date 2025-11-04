import maya.cmds as cmds

def copy_animation_between_rigs(source_ns, target_ns, control_list=None, time_range=None):
    """
    Copy animation from one rig to another, matching controls by name but allowing for different namespaces.
    Only copies animation for controls that exist in both rigs.
    
    Args:
        source_ns (str): Source rig namespace (e.g., 'SourceRig:')
        target_ns (str): Target rig namespace (e.g., 'TargetRig:')
        control_list (list, optional): List of control names (without namespace). If None, will auto-detect from source_ns.
        time_range (tuple, optional): (start, end) frame range. If None, uses playback range.
    """
    # Get time range
    if time_range is None:
        start = cmds.playbackOptions(q=True, min=True)
        end = cmds.playbackOptions(q=True, max=True)
    else:
        start, end = time_range
    
    # Get list of controls
    if control_list is None:
        # Find all top-level transforms in the source namespace
        all_source = cmds.ls(source_ns + '*', type='transform')
        control_list = [ctrl.split(':')[-1] for ctrl in all_source]
        control_list = list(set(control_list))  # Remove duplicates
    
    copied = []
    skipped = []
    for ctrl in control_list:
        src = source_ns + ctrl
        tgt = target_ns + ctrl
        if cmds.objExists(src) and cmds.objExists(tgt):
            try:
                cmds.copyKey(src, time=(start, end))
                cmds.pasteKey(tgt, time=(start, end), option='replaceCompletely')
                copied.append(ctrl)
            except Exception as e:
                print(f"Failed to copy {ctrl}: {e}")
                skipped.append(ctrl)
        else:
            skipped.append(ctrl)
    
    print(f"Copied animation for {len(copied)} controls:")
    for c in copied:
        print(f"  {c}")
    if skipped:
        print(f"Skipped {len(skipped)} controls (missing in one or both rigs):")
        for c in skipped:
            print(f"  {c}")
    print("Done.")

# Example usage:
# copy_animation_between_rigs('SourceRig:', 'TargetRig:')
# or specify controls:
# copy_animation_between_rigs('A:', 'B:', ['Main_CON', 'Root_CON'])

if __name__ == "__main__":
    # Example: change these to your namespaces
    copy_animation_between_rigs('SourceRig:', 'TargetRig:')
