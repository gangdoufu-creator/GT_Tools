import maya.cmds as cmds
import gt_utilities as gt


def createDriverRowUI(layoutParent):
    cmds.setParent(layoutParent)
    driverLayout = cmds.columnLayout(adjustableColumn=True)
    cmds.rowLayout(nc=3, columnWidth=(80, 250), adjustableColumn=3)  
    cmds.text(label='  Driver  ', edit=False)
    cmds.button(label=">>", width=120, command=lambda *args: cmds.textFieldGrp(driverName, edit=True, text=gt.get_selection_name()))
    driverName = cmds.textFieldGrp(label="", columnWidth2=(0, 170), adjustableColumn2=2)
    return driverName

def bake_objs(objs):
    cmds.select(objs)
    # Set the start and end frames for baking
    start_frame = cmds.playbackOptions(q=True, min=True)
    end_frame = cmds.playbackOptions(q=True, max=True)
    # Bake the animation on each selected object
    cmds.bakeResults(simulation=True, t=(start_frame, end_frame))
    # Deselect all objects
    cmds.select(clear=True)
   
def bake_rigs(rig):  
    # Get the rig name from the text field  
    rig = cmds.textFieldGrp(rig, q=True, text=True)      
    # Get a list of the controls to be baked
    controls_to_bake = sorted(cmds.sets( rig, q=True ), key=str.lower)  
    # Select all objects in the list
    bake_objs(controls_to_bake)
    # Delete all associated blend nodes and locators
    # Get a list of all nodes in the scene
    all_nodes = cmds.ls()
    # Loop over each node and delete it if its name contains 'blendColors_animBlend'
   
    for node in all_nodes:
        try:
            if 'rig_connector' in node:
                cmds.delete(node)
        except ValueError:
            continue

def connect_rigs(rigs):      

    # get the name of the rig control set from the ui text fields eg. DP1:Deadpool_AutoRig  
    for x in range(0,len(rigs)-1,1):
        rigs[x] = cmds.textFieldGrp(rigs[x], q=True, text=True)

    # Create a locator to store the blend settings
    rig_connector_settings = cmds.spaceLocator(name="rig_connector_settings")[0]  

    # Add custom channels to the locator
   
   
    # These variables only act on the driver rigs so require one less increment    
    for x in range(0,len(rigs)-1,1):
        # Creates one blend channel for each driver rig
        cmds.addAttr(rig_connector_settings, longName="rigBlend"+ str(x), attributeType="float", keyable=True, minValue=0.0, maxValue=1.0, defaultValue=0.5)    
        # change the rig name to a list of all the controls in the rig from the controls set.  These need to be sorted as the sets fucntion doesn't return them in the same order e
        rigs[x] = sorted(cmds.sets( rigs[x], q=True ), key=str.lower)  
   
    # Lock and hide the transform channels
    for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "visibility"]:
        cmds.setAttr(rig_connector_settings + "." + attr, lock=True, keyable=False, channelBox=False)
           
    try:                                    
        # Connects all the controls on the driver rigs to the target rig                
        for i in range(len(rigs[0])):
            # these are the keyable attributes on that control
            keyableAttrs = cmds.listAttr(rigs[0][i], keyable=True, unlocked=True, visible=True)            
            # checks if there are no keyable attributes on this control.  If not then skip to next control
            if keyableAttrs is None:
                continue
            else:                                
                for j in range(len(keyableAttrs)):    
                    # one multdiv node for each attr connection              
                    multDiv_node = []
                    test = []
                    for x in range(len(rigs)-2):      
                        multDiv_node.append(cmds.createNode('multiplyDivide', name = "multDiv_rig_connector"))
                        # connect the three attributes from the source rigs to the multiDiv node
                        cmds.connectAttr(rigs[x+1][i] + "." + keyableAttrs[j], multDiv_node[x]+'.input1X')                  
                        # connect rigblend attributes on the blender_locator_settings to the multipliers
                        cmds.connectAttr(rig_connector_settings+".rigBlend"+str(x), multDiv_node[x]+'.input2X')
                                         
                    # plusMinus node which averages out all the rig controls and feeds into the target
                    plusMinus_node = cmds.createNode('plusMinusAverage', name = "plusMinus_rig_connector")                
                    # connect the three attributes from the multiDiv nodes to the plusMinsAverage Node                      
                    for x in range(len(rigs)-2):                
                        cmds.connectAttr(multDiv_node[x]+'.outputX', plusMinus_node+ ".input1D[" + str(x) + "]")
                   
                    # disconnect the destination attribute if it's connected
                    #gt.disconnectAttr_if_connected(rigs[0][i] + "." + keyableAttrs[j])      
                   
                    # Now connect the output of the blend node into the target rig attribute      
                    cmds.connectAttr(plusMinus_node+".output1D", rigs[0][i] + "." + keyableAttrs[j])                                                          

    except TypeError:
        print("Are these rig topnodes or the control sets?  Please make sure its the control sets used.")
       
def addBakeRow_and_connectRigs(driverRow, bakeRow):
    # add the bake row rig here so it goes at the end of the list
    driverRow.append(bakeRow)  
    # remove any empty strings from the list
    driverRow = [x for x in driverRow if x]
    # connect the rigs
    connect_rigs(driverRow)  
           
def create_selection_name_input_ui():
   
    winWidth = 450
    driverRow = []
    
    """Creates a UI window for inputting the name of the selection."""
    # Create a new window
    window = cmds.window(title="rigConnector", sizeable=True)
    mainCL = cmds.columnLayout(adjustableColumn=True, width=winWidth)
   
    rowWidth = [ winWidth*0.5, winWidth*0.5]
   
    # Target Group
    cmds.frameLayout(label=" ")
    cmds.columnLayout(adjustableColumn=True)
    cmds.rowLayout(nc=3, columnWidth2=rowWidth, adjustableColumn=3)
    cmds.text(label='  Target     ', edit=False)
    cmds.button(label=">>", width=120, command=lambda *args: cmds.textFieldGrp(rig0, edit=True, text=gt.get_selection_name()))
    # This is just assigning the textfield name to rig0
    driverRow.append(cmds.textFieldGrp(label="", columnWidth2=(0, 170), adjustableColumn2=2))
    cmds.setParent(mainCL)
   
    # Add aDriver
    addDriverLayout = cmds.columnLayout(adjustableColumn=True)
    cmds.button(label="Add Driver", width=330, command=lambda *args: driverRow.append(createDriverRowUI(addDriverLayout)))
           
    # Driver 1 Group   
    driverRow.append(createDriverRowUI('..'))
    cmds.setParent('..') 
    # Driver 1 Group       
    secondDriverLayout = driverRow.append(createDriverRowUI('..'))
    cmds.setParent('..')    
  
    # Add a button to initiate the rig connection process
    cmds.button(label="Connect Rigs", width=330, command=lambda *args: addBakeRow_and_connectRigs(driverRow, bakeRow))
    
    # Creat the Bake Group ui
    cmds.columnLayout(adjustableColumn=True)
    cmds.rowLayout(nc=3, columnWidth2=(80, 250), adjustableColumn=3)    
    cmds.text(label=' Bake Me  ', edit=False)
    cmds.button(label=">>>", width=120, command=lambda *args: cmds.textFieldGrp(bakeRow, edit=True, text=gt.get_selection_name()))
    bakeRow = cmds.textFieldGrp(label="bake", editable=True, columnWidth2=(0, 170), adjustableColumn2=2)
    cmds.setParent('..')
    cmds.setParent('..')
 
    # Add a button to initiate the blending process    
    cmds.button(label="Bake Rigs", width=330, command=lambda *args: bake_rigs(rig4))
 
    # gets selection to put into text fields automatically
    selection = cmds.ls(selection=True)
    
    
    if selection:
        if len(selection)<4:            
            for selected, driver in zip(selection, driverRow):
                cmds.textFieldGrp(driver, edit=True, text=selected)               
        else:
            for i in range(len(selection)-3):
                driverRow.append(createDriverRowUI(addDriverLayout))                
            for selected, driver in zip(selection, driverRow):
                cmds.textFieldGrp(driver, edit=True, text=selected)        
    cmds.textFieldGrp(bakeRow, edit=True, text=selection[0]) 
    
    
          
   
    # Show the window
    cmds.showWindow(window)
create_selection_name_input_ui()
