import os
import pathlib
import adsk.core

from .. import config
from .. import utility as futil
from . import exporter

CMD_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_exporter"
CMD_NAME = "Export Project"
CMD_DESC = "Export the current project."

IS_PROMOTED = True

WORKSPACE_ID = "FusionSolidEnvironment"
TOOLBAR_PANEL_ID = "SolidScriptsAddinsPanel"
COMMAND_BESIDE_ID = "ScriptsManagerCommand"

ICON_FOLDER = config.ADDIN_PATH / "media" / "icons"

_handlers = []

app = adsk.core.Application.get()
ui = app.userInterface

def start():
    # Create the command definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_DESC, str(ICON_FOLDER)
    )
    futil.add_handler(cmd_def.commandCreated, command_created)

    # Add the command to the toolbar.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED


def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    inputs = args.command.commandInputs

    args.command.okButtonText = "Export"
    args.command.isRepeatable = True
    args.command.setDialogInitialSize(200, 400)

    # Current project
    try:
        project_name = app.data.activeProject.name
    except Exception:
        ui.messageBox("No active project found. Please select a project in the Data Panel.")
        return
    project_input = inputs.addTextBoxCommandInput("project", "Project to export", "", 1, True)
    project_input.tooltipDescription = "To change the project, change the active project in the Data Panel."
    project_input.text = project_name

    # Destination Folder
    dest = inputs.addBoolValueInput("open_folder", "Destination Folder", False, "", False)
    dest.tooltipDescription = "The folder to export the project to."
    dest.text = " Choose... "
    dest_path = inputs.addTextBoxCommandInput("folder_path", "", "", 1, True)
    dest_path.isVisible = False

    # Export file type
    text_dropdown_type = adsk.core.DropDownStyles.TextListDropDownStyle
    file_dropdown = inputs.addDropDownCommandInput("file_type", "Export As", text_dropdown_type)
    file_dropdown.listItems.add("f3d", True)
    file_dropdown.listItems.add("step", False)
    file_dropdown.listItems.add("stl", False)
    file_dropdown.listItems.add("obj", False)
    file_dropdown.tooltipDescription = "The file type to export all designs in the project."

    # Reference Behaviour
    ref_dropdown = inputs.addDropDownCommandInput("reference", "Reference Behaviour", text_dropdown_type)
    ref_dropdown.listItems.add("Ignore Design", True)
    ref_dropdown.listItems.add("Break References", False)
    ref_dropdown.tooltipDescription = "Behaviour when exporting a design that references other designs."

    # Options
    v = inputs.addBoolValueInput("all_versions", "Include All Versions", True, "", False)
    v.tooltipDescription = "Include all versions of the design in the export."

    # Connect events triggered by this command
    global _handlers
    futil.add_handler(args.command.inputChanged, on_input_changed, local_handlers=_handlers)
    futil.add_handler(args.command.validateInputs, on_validate, local_handlers=_handlers)
    futil.add_handler(args.command.execute, on_execute, local_handlers=_handlers)
    futil.add_handler(args.command.destroy, on_destroy, local_handlers=_handlers)


def on_validate(args: adsk.core.ValidateInputsEventArgs):
    folder_path_input = adsk.core.TextBoxCommandInput.cast(
        args.inputs.itemById("folder_path"))
    folder_path = folder_path_input.text

    if not os.path.exists(folder_path):
        args.areInputsValid = False
        return

    args.areInputsValid = True


def on_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input

    if changed_input.id == "open_folder":
        dialog = ui.createFolderDialog()
        dialog.title = "Select Export Folder"
        dialog_result = dialog.showDialog()

        if dialog_result == adsk.core.DialogResults.DialogOK:
            temp = args.inputs.itemById("folder_path")
            folder_path = adsk.core.TextBoxCommandInput.cast(temp)
            folder_path.isVisible = True
            folder_path.text = dialog.folder


def on_execute(args: adsk.core.CommandEventArgs):
    folder_path_input = adsk.core.TextBoxCommandInput.cast(
        args.command.commandInputs.itemById("folder_path"))
    file_type_input = adsk.core.DropDownCommandInput.cast(
        args.command.commandInputs.itemById("file_type"))
    reference_input = adsk.core.DropDownCommandInput.cast(
        args.command.commandInputs.itemById("reference"))
    all_versions_input = adsk.core.BoolValueCommandInput.cast(
        args.command.commandInputs.itemById("all_versions"))

    # Collect input values
    folder_path = pathlib.Path(folder_path_input.text)
    file_type = file_type_input.selectedItem.name
    reference_behaviour = reference_input.selectedItem.name
    all_versions = all_versions_input.value

    # Export the project
    try:
        exporter.export(folder_path, file_type, reference_behaviour, all_versions)
    except Exception as e:
        futil.handle_error(f"Export failed: {e}", show_message_box=True)
        return

    ui.messageBox(f"Export complete: {folder_path}")


def on_destroy(args: adsk.core.CommandEventArgs):
    global _handlers
    _handlers = []
