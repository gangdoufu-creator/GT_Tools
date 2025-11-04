import maya.cmds as cmds

class CopyAnimBetweenRigsUI:
    def __init__(self):
        self.window = 'CopyAnimBetweenRigsUI'
        self.title = 'Copy Animation Between Rigs'
        self.size = (420, 340)

    def show(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        self.build_ui()
        cmds.showWindow(self.window)

    def build_ui(self):
        self.window = cmds.window(self.window, title=self.title, widthHeight=self.size, sizeable=False)
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
        cmds.text(label='Copy Animation Between Rigs', font='boldLabelFont', height=30)
        cmds.separator(height=10)

        # Namespaces with selection buttons (6 columns)
        cmds.rowLayout(numberOfColumns=6, columnWidth6=(100, 100, 30, 100, 100, 30), adjustableColumn=2)
        cmds.text(label='Source Namespace:')
        self.source_ns = cmds.textField(text='Proxy_Version_But_Bined_Skin_Instead:')
        self.src_sel_btn = cmds.button(label='<<', width=30, command=self.set_source_ns_from_selection)
        cmds.text(label='Target Namespace:')
        self.target_ns = cmds.textField(text='No_Tail_Spine_Rig:')
        self.tgt_sel_btn = cmds.button(label='<<', width=30, command=self.set_target_ns_from_selection)
        cmds.setParent('..')

        # Controls with add selection button
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(120, 220, 60), adjustableColumn=2)
        cmds.text(label='Control List (optional):')
        self.controls_field = cmds.textField(text='', placeholderText='Auto-detects from ControlSet or leave blank')
        self.add_sel_btn = cmds.button(label='Add Sel', width=60, command=self.add_selection_to_controls)
        cmds.setParent('..')

        cmds.separator(height=10)
        cmds.button(label='Copy Animation', height=40, bgc=(0.3,0.6,0.3), command=self.copy_anim)
        cmds.separator(height=10)
        self.result_field = cmds.scrollField(editable=False, wordWrap=True, height=120, text='')

    def set_source_ns_from_selection(self, *args):
        sel = cmds.ls(selection=True, long=True)
        if sel:
            # Get namespace from first selected object
            parts = sel[0].split(':')
            if len(parts) > 1:
                ns = ':'.join(parts[:-1]) + ':'
                cmds.textField(self.source_ns, edit=True, text=ns)

    def set_target_ns_from_selection(self, *args):
        sel = cmds.ls(selection=True, long=True)
        if sel:
            parts = sel[0].split(':')
            if len(parts) > 1:
                ns = ':'.join(parts[:-1]) + ':'
                cmds.textField(self.target_ns, edit=True, text=ns)

    def add_selection_to_controls(self, *args):
        sel = cmds.ls(selection=True, long=True)
        if sel:
            # Remove namespaces and leading '|' from selection
            names = [s.split(':')[-1].lstrip('|') for s in sel]
            # Merge with existing field
            current = cmds.textField(self.controls_field, q=True, text=True)
            current_list = [c.strip().lstrip('|') for c in current.split(',') if c.strip()]
            merged = list(dict.fromkeys(current_list + names))  # Remove duplicates, preserve order
            cmds.textField(self.controls_field, edit=True, text=', '.join(merged))

    def copy_anim(self, *args):
        src_ns = cmds.textField(self.source_ns, q=True, text=True).strip()
        tgt_ns = cmds.textField(self.target_ns, q=True, text=True).strip()
        controls_text = cmds.textField(self.controls_field, q=True, text=True)
        debug_log = ''
        
        if not src_ns or not tgt_ns:
            cmds.warning('Please enter both source and target namespaces.')
            return
        
        # Ensure namespaces end with ':'
        if not src_ns.endswith(':'):
            src_ns += ':'
        if not tgt_ns.endswith(':'):
            tgt_ns += ':'
        
        # Parse controls
        if controls_text.strip():
            control_list = [c.strip().lstrip('|').lstrip('|') for c in controls_text.split(',') if c.strip()]
        else:
            # Try to find ControlSet in the source namespace
            control_set_name = src_ns + 'ControlSet'
            if cmds.objExists(control_set_name) and cmds.objectType(control_set_name) == 'objectSet':
                # Get all members of the set
                set_members = cmds.sets(control_set_name, query=True) or []
                debug_log += f'Found ControlSet: {control_set_name} with {len(set_members)} members\n'
                # Extract short names without namespace
                control_list = [obj.split(':')[-1].lstrip('|').strip() for obj in set_members]
                debug_log += f'Using {len(control_list)} controls from ControlSet\n'
            else:
                # Fallback: Auto-detect from source namespace
                debug_log += f'ControlSet not found at {control_set_name}, using auto-detect\n'
                all_source = cmds.ls(src_ns + '*', type='transform')
                control_list = [ctrl.split(':')[-1].lstrip('|').lstrip('|') for ctrl in all_source]
                control_list = list(set(control_list))
        
        copied = []
        skipped = []
        for ctrl in control_list:
            # Clean control name - remove any leading pipes or hierarchy separators
            ctrl_clean = ctrl.lstrip('|').lstrip('|').strip()
            
            # Build full paths WITHOUT any leading pipes
            src = src_ns + ctrl_clean
            tgt = tgt_ns + ctrl_clean
            
            src_exists = cmds.objExists(src)
            tgt_exists = cmds.objExists(tgt)
            debug_log += f'Checking {ctrl_clean}:\n  Source: {src} exists={src_exists}\n  Target: {tgt} exists={tgt_exists}\n'
            
            if src_exists and tgt_exists:
                anim_attrs = cmds.listAnimatable(src) or []
                anim_attrs_with_keys = []
                for attr in anim_attrs:
                    key_count = cmds.keyframe(attr, query=True, keyframeCount=True)
                    if key_count and key_count > 0:
                        anim_attrs_with_keys.append(attr)
                debug_log += f'  Animatable attributes with keys: {len(anim_attrs_with_keys)}\n'
                if not anim_attrs_with_keys:
                    skipped.append(f'{ctrl_clean} (no animation curves)')
                    continue
                    
                # Copy animation for each attribute
                attrs_copied = 0
                for attr in anim_attrs_with_keys:
                    try:
                        cmds.copyKey(attr)
                        tgt_attr = tgt + '.' + attr.split('.')[-1]
                        if cmds.objExists(tgt_attr):
                            cmds.pasteKey(tgt_attr, option='replaceCompletely')
                            attrs_copied += 1
                        else:
                            debug_log += f'    Target attribute missing: {tgt_attr}\n'
                    except Exception as e:
                        skipped.append(f'{ctrl_clean}.{attr.split(".")[-1]} (error: {e})')
                        debug_log += f'    Error copying {attr}: {e}\n'
                
                if attrs_copied > 0:
                    copied.append(f'{ctrl_clean} ({attrs_copied} attrs)')
                    debug_log += f'  Successfully copied {attrs_copied} attributes\n'
            else:
                if not src_exists:
                    debug_log += f'  Source control missing!\n'
                if not tgt_exists:
                    debug_log += f'  Target control missing!\n'
                skipped.append(ctrl_clean)
        result = f'Copied animation for {len(copied)} controls:\n'
        for c in copied:
            result += f'  {c}\n'
        if skipped:
            result += f'\nSkipped {len(skipped)} controls/attributes (missing or error):\n'
            for c in skipped:
                result += f'  {c}\n'
        result += '\n--- DEBUG LOG ---\n' + debug_log
        cmds.scrollField(self.result_field, edit=True, text=result)
        print(result)

# To launch the UI:
def show_copy_anim_between_rigs_ui():
    ui = CopyAnimBetweenRigsUI()
    ui.show()

if __name__ == '__main__':
    show_copy_anim_between_rigs_ui()
