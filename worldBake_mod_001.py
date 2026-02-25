# -= ml_worldBake_shelf.py =-
# Standalone version of ml_worldBake.py without ml_utilities dependency
# Launches GUI directly when run - perfect for shelf buttons
#
# Based on ml_worldBake.py by Morgan Loomis
# Modified to be self-contained

from functools import partial
import maya.cmds as mc
from maya import OpenMaya

def frameRange():
    """Get the current frame range"""
    start = mc.playbackOptions(query=True, minTime=True)
    end = mc.playbackOptions(query=True, maxTime=True)
    return start, end

def getCurrentCamera():
    """Returns the camera that you're currently looking through"""
    panel = mc.getPanel(withFocus=True)
    
    if mc.getPanel(typeOf=panel) != 'modelPanel':
        for p in mc.getPanel(visiblePanels=True):
            if mc.getPanel(typeOf=p) == 'modelPanel':
                panel = p
                mc.setFocus(panel)
                break
    
    if mc.getPanel(typeOf=panel) != 'modelPanel':
        OpenMaya.MGlobal.displayWarning('Please highlight a camera viewport.')
        return None
        
    camShape = mc.modelPanel(panel, query=True, camera=True)
    if not camShape:
        return None
        
    if mc.nodeType(camShape) == 'transform':
        return camShape
    elif mc.nodeType(camShape) in ['camera','stereoRigCamera']:
        return mc.listRelatives(camShape, parent=True, path=True)[0]

def matchBake(source=None, destination=None, bakeOnOnes=False, maintainOffset=False):
    """Simplified match bake function"""
    if not source and not destination:
        sel = mc.ls(sl=True)
        if len(sel) != 2:
            OpenMaya.MGlobal.displayWarning('Select exactly 2 objects')
            return
        source = [sel[0]]
        destination = [sel[1]]
    
    resetTime = mc.currentTime(query=True)
    start, end = frameRange()
    
    attributes = ['translateX','translateY','translateZ','rotateX','rotateY','rotateZ']
    
    duplicates = {}
    constraint = list()
    allKeyTimes = [start, end]
    keytimes = {}
    
    for s, d in zip(source, destination):
        dup = mc.duplicate(d, name='temp#', parentOnly=True)[0]
        for a in attributes:
            mc.setAttr(dup+'.'+a, lock=False, keyable=True)
        
        constraint.append(mc.parentConstraint(s, dup, maintainOffset=maintainOffset))
        
        # Only cut keys from transform attributes, preserving other channels (like camera focal length)
        for attr in attributes:
            try:
                mc.cutKey(d, attribute=attr, time=(start,end))
            except:
                pass
        
        duplicates[d] = dup
        keytimes[d] = {}
        
        if not bakeOnOnes:
            for a in attributes:
                currKeytimes = mc.keyframe(s, attribute=a, time=(start,end), query=True, timeChange=True)
                if currKeytimes:
                    keytimes[d][a] = currKeytimes
                    allKeyTimes.extend(currKeytimes)
    
    if bakeOnOnes:
        allKeyTimes = list(range(int(start), int(end)+1))
    else:
        allKeyTimes = list(set(allKeyTimes))
        allKeyTimes.sort()
    
    for frame in allKeyTimes:
        mc.currentTime(frame, edit=True)
        for d in destination:
            for a in attributes:
                try:
                    v = mc.getAttr(duplicates[d]+'.'+a)
                    mc.setKeyframe(d, attribute=a, time=frame, value=v)
                except:
                    pass
    
    mc.delete(list(duplicates.values()))
    mc.currentTime(resetTime, edit=True)

def currentFrameConstraint(firstObj, parent, setToZero=False, maintainOffset=True):
    """Creates a locator parented to parent, positioned at firstObj, then constrains firstObj to it"""
    if not firstObj or not parent:
        OpenMaya.MGlobal.displayWarning('Error: invalid objects.')
        return None
    
    name = mc.ls(firstObj, shortNames=True)[0]
    if ':' in name:
        name = firstObj.rpartition(':')[-1]
    
    locator = mc.spaceLocator(name='worldBake_'+name+'_#')[0]
    mc.setAttr(locator+'.rotateOrder', 3)
    
    mc.addAttr(locator, longName='ml_bakeSource', attributeType='message')
    mc.addAttr(locator, longName='ml_bakeSourceName', dataType='string')
    mc.setAttr(locator+'.ml_bakeSourceName', name, type='string')
    
    try:
        mc.connectAttr(f"{firstObj}.message", f"{locator}.ml_bakeSource")
    except:
        pass
    
    mc.matchTransform(locator, firstObj, position=True, rotation=True, scale=False)
    mc.parent(locator, parent, absolute=True)
    mc.makeIdentity(locator, apply=True, translate=True, rotate=True, scale=False)
    
    try:
        unlocked_translate = [attr for attr in ['translateX', 'translateY', 'translateZ'] 
                              if not mc.getAttr(f"{firstObj}.{attr}", lock=True)]
        unlocked_rotate = [attr for attr in ['rotateX', 'rotateY', 'rotateZ'] 
                           if not mc.getAttr(f"{firstObj}.{attr}", lock=True)]
        
        if unlocked_translate:
            mc.pointConstraint(locator, firstObj, maintainOffset=maintainOffset)
        if unlocked_rotate:
            mc.orientConstraint(locator, firstObj, maintainOffset=maintainOffset)
    except RuntimeError as e:
        OpenMaya.MGlobal.displayWarning(f"Constraint failed: {e}")
    
    if setToZero:
        mc.setAttr(locator + '.translate', 0, 0, 0)
        mc.setAttr(locator + '.rotate', 0, 0, 0)
    
    return locator

def toLocators(bakeOnOnes=False, space='world', spaceInt=None, constrainSource=False, currentFrameOnly=False, setToZero=False, maintainOffset=True):
    """Creates locators and bakes their position to selection"""
    if spaceInt is not None and 0 <= spaceInt <= 2:
        space = ['world', 'camera', 'last'][spaceInt]
    
    sel = mc.ls(sl=True)
    parent = None
    if space == 'camera':
        parent = getCurrentCamera()
    elif space == 'last':
        parent = sel[-1]
        sel = sel[:-1]
    
    if currentFrameOnly:
        if not sel or not parent:
            OpenMaya.MGlobal.displayWarning('Select objects, with the parent as the last selection.')
            return
        locator = currentFrameConstraint(sel[0], parent, setToZero=setToZero, maintainOffset=maintainOffset)
        if locator:
            mc.select(locator)
    else:
        mc.select(sel)
        locs = matchBakeLocators(parent=parent, bakeOnOnes=bakeOnOnes, constrainSource=constrainSource)
        if locs:
            mc.select(locs)

def fromLocators(bakeOnOnes=False, maintainOffset=True):
    """Traces connections from selected locators to their source nodes and bakes back"""
    objs = mc.ls(sl=True)
    if not objs:
        OpenMaya.MGlobal.displayWarning('Select a previously baked locator.')
        return
    
    source = list()
    destination = list()
    
    for src in objs:
        try:
            if not mc.attributeQuery('ml_bakeSource', node=src, exists=True):
                continue
            
            dest = mc.listConnections(src+'.ml_bakeSource', destination=False)
            if not dest:
                continue
            
            dest = dest[0]
            source.append(src)
            destination.append(dest)
        except:
            pass
    
    if not destination:
        OpenMaya.MGlobal.displayWarning('Select a previously baked locator.')
        return
    
    matchBake(source=source, destination=destination, bakeOnOnes=bakeOnOnes, maintainOffset=maintainOffset)
    
    for each in source:
        try:
            mc.delete(each)
        except:
            pass

def matchBakeLocators(parent=None, bakeOnOnes=False, constrainSource=False):
    """Create locators for selected objects and bake animation to them"""
    objs = mc.ls(sl=True)
    if not objs:
        OpenMaya.MGlobal.displayWarning('Select an Object')
        return None
    
    locs = list()
    noKeys = list()
    noKeysLoc = list()
    
    for obj in objs:
        name = mc.ls(obj, shortNames=True)[0]
        if ':' in name:
            name = obj.rpartition(':')[-1]
        
        locator = mc.spaceLocator(name='worldBake_'+name+'_#')[0]
        mc.setAttr(locator+'.rotateOrder', 3)
        
        mc.addAttr(locator, longName='ml_bakeSource', attributeType='message')
        mc.connectAttr('.'.join((obj,'message')), '.'.join((locator,'ml_bakeSource')))
        mc.addAttr(locator, longName='ml_bakeSourceName', dataType='string')
        mc.setAttr('.'.join((locator,'ml_bakeSourceName')), name, type='string')
        
        if parent:
            locator = mc.parent(locator, parent)[0]
        
        locs.append(locator)
        
        if not mc.keyframe(obj, query=True, name=True):
            noKeys.append(obj)
            noKeysLoc.append(locator)
    
    matchBake(objs, locs, bakeOnOnes=bakeOnOnes)
    
    if not bakeOnOnes and noKeys:
        matchBake(noKeys, noKeysLoc, bakeOnOnes=True)
    
    if constrainSource:
        # Only cut keys from transform attributes, preserving other channels (like camera focal length)
        transform_attrs = ['translateX','translateY','translateZ','rotateX','rotateY','rotateZ']
        for obj in objs:
            for attr in transform_attrs:
                try:
                    mc.cutKey(obj, attribute=attr)
                except:
                    pass
        for loc, obj in zip(locs, objs):
            mc.parentConstraint(loc, obj)
    
    return locs

def reparent(bakeOnOnes=False):
    """Re-parent selected objects to last selection"""
    objs = mc.ls(sl=True)
    if not objs or len(objs) < 2:
        OpenMaya.MGlobal.displayWarning('Select one or more nodes, followed by the new parent.')
        return
    parentBake(objs[:-1], objs[-1], bakeOnOnes=bakeOnOnes)

def unparent(bakeOnOnes=False):
    """Un-parent selected objects to world"""
    objs = mc.ls(sl=True)
    if not objs:
        OpenMaya.MGlobal.displayWarning('Select one or more nodes to unparent.')
        return
    parentBake(objs, bakeOnOnes=bakeOnOnes)

def parentBake(objs, parent=None, bakeOnOnes=False):
    """Bake and reparent objects"""
    parentReferenced = mc.referenceQuery(parent, isNodeReferenced=True) if parent else False
    
    culledObjs = []
    for each in objs:
        eachParent = mc.listRelatives(each, parent=True)
        if mc.referenceQuery(each, isNodeReferenced=True):
            if parentReferenced:
                OpenMaya.MGlobal.displayWarning("Child and parent are both referenced, skipping: {} > {}".format(each, parent))
                continue
            if eachParent and mc.referenceQuery(eachParent[0], isNodeReferenced=True):
                OpenMaya.MGlobal.displayWarning("Node is referenced and can't be reparented, skipping: {}".format(each))
                continue
        if not parent and not eachParent:
            OpenMaya.MGlobal.displayWarning("Node is already child of the world, skipping: {}".format(each))
            continue
        culledObjs.append(each)
    
    if not culledObjs:
        OpenMaya.MGlobal.displayWarning("No nodes could be reparented.")
        return
    
    source = []
    destination = []
    for each in culledObjs:
        source.append(mc.duplicate(each, parentOnly=True)[0])
        mc.copyKey(each)
        mc.pasteKey(source[-1], option='replaceCompletely')
        try:
            if parent:
                destination.append(mc.parent(each, parent)[0])
            else:
                destination.append(mc.parent(each, world=True)[0])
        except RuntimeError as err:
            mc.delete(source)
            raise err
    
    matchBake(source=source, destination=destination, bakeOnOnes=bakeOnOnes)
    mc.delete(source)

def ui():
    """User interface for world bake"""
    windowName = 'ml_worldBake_shelf'
    
    if mc.window(windowName, exists=True):
        mc.deleteUI(windowName)
    
    window = mc.window(windowName, title='World Bake', width=400, height=200, menuBar=True)
    
    # Create menu
    mc.menu(label='Help')
    mc.menuItem(label='About', command=lambda *args: mc.confirmDialog(title='About', message='ml_worldBake - Standalone Version\nBased on ml_worldBake.py by Morgan Loomis', button=['Close']))
    
    # Main layout
    form = mc.formLayout()
    column = mc.columnLayout(adj=True)
    
    # Info header
    mc.rowLayout(numberOfColumns=2, columnWidth2=(34, 366), adjustableColumn=2, 
                 columnAlign2=('right','left'), 
                 columnAttach=[(1, 'both', 0), (2, 'both', 8)])
    mc.text(label=' _ _ |\n| | | |')
    mc.text(label='Select objects, bake to locators in world, camera, or custom space.\nWhen you\'re ready to bake back, select locators\nand bake "from locators" to re-apply your animation.')
    mc.setParent('..')
    mc.separator(height=8, style='single', horizontal=True)
    
    # Bake on ones checkbox
    mc.checkBoxGrp('ml_worldBake_bakeOnOnes_checkBox', label='Bake on Ones', value1=True,
                   annotation='Bake every frame. If deselected, the tool will preserve keytimes.')
    
    # Tabs
    tabs = mc.tabLayout()
    
    # Tab 1: Bake To Locators
    tab1 = mc.columnLayout(adj=True)
    mc.radioButtonGrp('ml_worldBake_space_radioButton', label='Bake To Space', numberOfRadioButtons=3,
                      labelArray3=('World','Camera','Last Selected'), select=1,
                      annotation='The locators will be parented to world, the current camera, or the last selection.')
    mc.checkBoxGrp('ml_worldBake_constrain_checkBox', label='Maintain Constraints', value1=True,
                   annotation='Constrain source nodes to the created locators, after baking.')
    mc.separator(height=8, style='single', horizontal=True)
    mc.checkBoxGrp('ml_worldBake_currentFrameOnly_checkBox', label='Current Frame Only',
                   annotation='Create constraint to locator parented to last selected object (no animation baking).')
    mc.checkBoxGrp('ml_worldBake_setToZero_checkBox', label='Set Locator to Zero',
                   annotation='Set the locator transforms to zero after creation.')
    mc.checkBoxGrp('ml_worldBake_maintainOffset_checkBox', label='Maintain Offset',
                   annotation='Maintain the offset between the locator and the first object when applying constraints.')
    
    mc.button(label='Bake Selection To Locators', 
              command=lambda *args: toLocators(
                  bakeOnOnes=mc.checkBoxGrp('ml_worldBake_bakeOnOnes_checkBox', q=True, v1=True),
                  spaceInt=mc.radioButtonGrp('ml_worldBake_space_radioButton', q=True, sl=True)-1,
                  constrainSource=mc.checkBoxGrp('ml_worldBake_constrain_checkBox', q=True, v1=True),
                  currentFrameOnly=mc.checkBoxGrp('ml_worldBake_currentFrameOnly_checkBox', q=True, v1=True),
                  setToZero=mc.checkBoxGrp('ml_worldBake_setToZero_checkBox', q=True, v1=True),
                  maintainOffset=mc.checkBoxGrp('ml_worldBake_maintainOffset_checkBox', q=True, v1=True)
              ),
              annotation='Bake selected object to locators specified space.')
    mc.setParent('..')
    
    # Tab 2: Bake From Locators
    tab2 = mc.columnLayout(adj=True)
    mc.button(label='Bake Selected Locators Back To Objects',
              command=lambda *args: fromLocators(
                  bakeOnOnes=mc.checkBoxGrp('ml_worldBake_bakeOnOnes_checkBox', q=True, v1=True)
              ),
              annotation='Bake from selected locators back to their source objects.')
    mc.setParent('..')
    
    # Tab 3: Bake Selection
    tab3 = mc.columnLayout(adj=True)
    mc.button(label='Re-Parent Animated',
              command=lambda *args: reparent(
                  bakeOnOnes=mc.checkBoxGrp('ml_worldBake_bakeOnOnes_checkBox', q=True, v1=True)
              ),
              annotation='Parent all selected nodes to the last selection.')
    mc.button(label='Un-Parent Animated',
              command=lambda *args: unparent(
                  bakeOnOnes=mc.checkBoxGrp('ml_worldBake_bakeOnOnes_checkBox', q=True, v1=True)
              ),
              annotation='Parent all selected to world.')
    
    mc.separator()
    
    mc.checkBoxGrp('ml_worldBake_maintainOffset2_checkBox', label='Maintain Offset',
                   annotation='Maintain the offset between nodes, rather than snapping.')
    mc.button(label='Bake Selected',
              command=lambda *args: matchBake(
                  bakeOnOnes=mc.checkBoxGrp('ml_worldBake_bakeOnOnes_checkBox', q=True, v1=True),
                  maintainOffset=mc.checkBoxGrp('ml_worldBake_maintainOffset2_checkBox', q=True, v1=True)
              ),
              annotation='Bake from the first selected object directly to the second.')
    
    mc.tabLayout(tabs, edit=True, tabLabel=((tab1, 'Bake To Locators'), (tab2, 'Bake From Locators'), (tab3, 'Bake Selection')))
    
    # Finalize layout
    mc.setParent(form)
    frame = mc.frameLayout(labelVisible=False)
    mc.helpLine()
    
    mc.formLayout(form, edit=True,
                  attachForm=((column, 'top', 0), (column, 'left', 0),
                              (column, 'right', 0), (frame, 'left', 0),
                              (frame, 'bottom', 0), (frame, 'right', 0)),
                  attachNone=((column, 'bottom'), (frame, 'top')))
    
    mc.showWindow(window)
    mc.window(window, edit=True, width=400, height=200)

# Launch the UI when the script is run
if __name__ == "__main__":
    ui()