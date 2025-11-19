import maya.cmds as mc
from ragdoll import interactive as ri

def select_and_assign():
    """
    Executes a series of select commands and runs `ri.assign_and_connect()` after each selection.
    Maintains the selection order in the hierarchy.
    """
    selections = [
        ["joint13", "joint14", "joint15", "joint16", "joint17", "joint18", "joint19", "joint20", "joint21", "joint22", "joint23", "joint24", "joint25", "joint26"],
        ["joint27", "joint28", "joint29", "joint30", "joint31", "joint32", "joint33", "joint34", "joint35", "joint36", "joint37", "joint38", "joint39", "joint40", "joint41", "joint42", "joint43"],
        ["joint44", "joint45", "joint46", "joint47", "joint48", "joint49", "joint50", "joint51", "joint52", "joint53", "joint54", "joint55", "joint56", "joint57", "joint58", "joint59", "joint60"],
        ["joint61", "joint62", "joint63", "joint64", "joint65", "joint66", "joint67", "joint68", "joint69", "joint70", "joint71", "joint72", "joint73", "joint74", "joint75", "joint76"],
        ["joint77", "joint77|joint78", "joint77|joint78|joint79", "joint77|joint78|joint79|joint80", "joint77|joint78|joint79|joint80|joint81", "joint77|joint78|joint79|joint80|joint81|joint82", "joint77|joint78|joint79|joint80|joint81|joint82|joint83", "joint77|joint78|joint79|joint80|joint81|joint82|joint83|joint84", "joint77|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85", "joint77|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86", "joint77|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87", "joint77|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87|joint88", "joint77|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87|joint88|joint89"],
        ["joint90", "joint90|joint78", "joint90|joint78|joint79", "joint90|joint78|joint79|joint80", "joint90|joint78|joint79|joint80|joint81", "joint90|joint78|joint79|joint80|joint81|joint82", "joint90|joint78|joint79|joint80|joint81|joint82|joint83", "joint90|joint78|joint79|joint80|joint81|joint82|joint83|joint84", "joint90|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85", "joint90|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86", "joint90|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87", "joint90|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87|joint88", "joint90|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87|joint88|joint89"],
        ["joint141", "joint142", "joint143", "joint144", "joint145", "joint146", "joint147", "joint148", "joint149", "joint150", "joint151", "joint152", "joint153", "joint154", "joint155", "joint156", "joint157", "joint158", "joint159", "joint160", "joint161"],
        ["joint126", "joint127", "joint128", "joint129", "joint130", "joint131", "joint132", "joint133", "joint134", "joint135", "joint136", "joint137", "joint138", "joint139", "joint140"],
        ["joint210", "joint211", "joint212", "joint213", "joint214", "joint215", "joint216", "joint217", "joint218", "joint219", "joint220", "joint221", "joint222", "joint223"],
        ["joint91", "joint91|joint78", "joint91|joint78|joint79", "joint91|joint78|joint79|joint80", "joint91|joint78|joint79|joint80|joint81", "joint91|joint78|joint79|joint80|joint81|joint82", "joint91|joint78|joint79|joint80|joint81|joint82|joint83", "joint91|joint78|joint79|joint80|joint81|joint82|joint83|joint84", "joint91|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85", "joint91|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86", "joint91|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87", "joint91|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87|joint88", "joint91|joint78|joint79|joint80|joint81|joint82|joint83|joint84|joint85|joint86|joint87|joint88|joint89"],
        ["joint191", "joint192", "joint193", "joint194", "joint195", "joint196", "joint197", "joint198", "joint199", "joint200", "joint201", "joint202", "joint203", "joint204", "joint205", "joint206", "joint207", "joint208", "joint209"],
        ["joint162", "joint163", "joint164", "joint165", "joint166", "joint167", "joint168", "joint169", "joint170", "joint171", "joint172", "joint173", "joint174", "joint175", "joint176", "joint177"],
        ["joint178", "joint179", "joint180", "joint181", "joint182", "joint183", "joint184", "joint185", "joint186", "joint187", "joint188", "joint189", "joint190"],
        ["FKEar_R", "FKEar1_R", "FKEar2_R", "FKEar3_R"],
        ["FKEar_L", "FKEar1_L", "FKEar2_L", "FKEar3_L"],
        ["joint211", "joint211|joint212", "joint211|joint212|joint213", "joint211|joint212|joint213|joint214", "joint211|joint212|joint213|joint214|joint215", "joint211|joint212|joint213|joint214|joint215|joint216", "joint211|joint212|joint213|joint214|joint215|joint216|joint217", "joint211|joint212|joint213|joint214|joint215|joint216|joint217|joint218", "joint211|joint212|joint213|joint214|joint215|joint216|joint217|joint218|joint219", "joint211|joint212|joint213|joint214|joint215|joint216|joint217|joint218|joint219|joint220"],
        ["joint225", "joint225|joint212", "joint225|joint212|joint213", "joint225|joint212|joint213|joint214", "joint225|joint212|joint213|joint214|joint215", "joint225|joint212|joint213|joint214|joint215|joint216", "joint225|joint212|joint213|joint214|joint215|joint216|joint217", "joint225|joint212|joint213|joint214|joint215|joint216|joint217|joint218", "joint225|joint212|joint213|joint214|joint215|joint216|joint217|joint218|joint219", "joint225|joint212|joint213|joint214|joint215|joint216|joint217|joint218|joint219|joint220"]
    ]
    

    for selection in selections:
        mc.select(selection, replace=True)
        ri.assign_and_connect()

# Run the function
select_and_assign()


objects = [
    "Fox_RIG_v001_RELEASE:pCube1",
    "Fox_RIG_v001_RELEASE:pCube3",
    "Fox_RIG_v001_RELEASE:pCube4",
    "Fox_RIG_v001_RELEASE:pCube5"
]

for obj in objects:
    mc.select(obj, r=True)
    ri.assign_marker()
    # The marker node is assumed to be named rMarker_<objectName>
    marker_name = "rMarker_" + obj.split(":")[-1]
    try:
        mc.setAttr(f"{marker_name}.inputType", 2)
    except Exception as e:
        print(f"Could not set inputType for {marker_name}: {e}")
