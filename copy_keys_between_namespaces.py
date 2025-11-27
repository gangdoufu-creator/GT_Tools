import maya.cmds as mc

def copy_keys_between_namespaces(source_namespace, target_namespace, source_suffix="_CON"):
    """
    Copies animation keys from objects in the source namespace to objects in the target namespace.

    Args:
        source_namespace (str): The namespace of the source objects (e.g., 'Proxy_Version_But_Bined_Skin_Instead').
        target_namespace (str): The namespace of the target objects (e.g., 'TyrantDragon_rig_Jaw_Control').
        source_suffix (str): The suffix of the source objects (default is '_CON').
    """
    # Get all objects in the source namespace with the specified suffix
    source_objects = mc.ls(f"{source_namespace}:*{source_suffix}", type="transform")

    if not source_objects:
        mc.warning(f"No objects found in namespace '{source_namespace}' with suffix '{source_suffix}'.")
        return

    for source_obj in source_objects:
        # Derive the target object name by replacing the namespace and removing the suffix
        base_name = source_obj.split(":")[-1].replace(source_suffix, "")
        target_obj = f"{target_namespace}:{base_name}"

        # Check if the target object exists
        if not mc.objExists(target_obj):
            mc.warning(f"Target object '{target_obj}' does not exist. Skipping.")
            continue

        # Copy animation keys from the source object to the target object
        try:
            mc.copyKey(source_obj)
            mc.pasteKey(target_obj, option="replaceCompletely")
            print(f"Successfully copied keys from '{source_obj}' to '{target_obj}'.")
        except RuntimeError as e:
            mc.warning(f"Failed to copy keys from '{source_obj}' to '{target_obj}': {e}")

# Example usage
copy_keys_between_namespaces(
    source_namespace="Proxy_Version_But_Bined_Skin_Instead",
    target_namespace="TyrantDragon_rig_Jaw_Control"
)