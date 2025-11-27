# Copyright (c) 2014 Lucasfilm Ltd. All rights reserved. Used under  
# authorization. This material contains the confidential and proprietary                                                                   
# information of Lucasfilm Ltd. and may not be copied in whole or in part                                                                  
# without the express written permission of Lucasfilm Ltd. This copyright                                                                  
# notice does not imply publication.  

# -----------------------------------------------------------------
#  Description:
#     Creates a camera, point constrains it to the selected
#     object, and looks through the new camera.
# -----------------------------------------------------------------
# Ported from trackCam.mel from /sww/gfx/lib/maya/scripts

import maya.cmds as cmds
import maya.OpenMaya as mApi

mInfo     = mApi.MGlobal.displayInfo
mWarning  = mApi.MGlobal.displayWarning
mError    = mApi.MGlobal.displayError

def do_trackCam(orient=False, lock=False):
    nodeList = cmds.ls(sl=True)
    if len(nodeList)>0:
        trackCam(nodeList[0], orient,lock)
    else:
        mError( "You gotta select something first!")
        return
        
    cmds.select(nodeList, r=True)

def trackCam(node,orient=False,lock=False):
    
    currentPanel = cmds.getPanel(withFocus=True)
    
    defaultCamera = False
    if not cmds.getPanel(typeOf=currentPanel) == 'modelPanel':
        if lock:
            mError( 'Active panel is not a modelPanel.  Set focus to the panel you wish to create a trackcam of by interacting with it,\n\
            and avoid hovering the mouse over other panels (like the outliner) before you run the tool.')
            return
        else:
            mInfo('Active panel is not a modelPanel.  Creating a default camera' )
            currentCamPos = cmds.xform(node, worldSpace=True, translation=True, query=True)
            defaultCamera = True
    else:
        currentCam = cmds.modelPanel(currentPanel, camera=True , query=True)
        currentCamPos = cmds.xform(currentCam, worldSpace=True, translation=True, query=True)

        
    destPos = cmds.xform(node, worldSpace=True, translation=True, query=True)

    tCam = cmds.camera(name=node.replace(':','_')+'_trackCam')
    tGroup = cmds.group(tCam[0], name=node.replace(':','_')+'_trackCam_GRP')

    cmds.xform(tGroup, objectSpace=True, pivots=destPos)
    
    cmds.pointConstraint(node, tGroup)
    
    if orient == True:
        cmds.orientConstraint(node, tGroup, maintainOffset=True)

    cmds.xform(tCam[0], worldSpace=True, translation=currentCamPos)

    cmds.lookThru(currentPanel, tCam[0])
    
    if defaultCamera:
        cmds.xform(tCam[0], objectSpace=True, relative=True, translation=(0,0,-10))
    cmds.viewLookAt(tCam[0], position=destPos)
    
    if lock == True:
        cmds.setAttr(tCam[0]+'.tx', lock=True)
        cmds.setAttr(tCam[0]+'.ty', lock=True)
        cmds.setAttr(tCam[0]+'.tz', lock=True)
        cmds.setAttr(tCam[0]+'.rx', lock=True)
        cmds.setAttr(tCam[0]+'.ry', lock=True)
        cmds.setAttr(tCam[0]+'.rz', lock=True)
        cmds.setAttr(tCam[1]+'.centerOfInterest', lock=True)
    
do_trackCam(orient=False, lock=False)
