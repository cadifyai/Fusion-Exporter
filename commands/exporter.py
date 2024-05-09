import pathlib
import adsk.core
import adsk.fusion
from .. import utility as futil


class ExportFailure(Exception):
    """Exception raised when an export operation fails."""
    def __init__(self, message: str):
        super().__init__(message)


class BreakLinkFailure(Exception):
    """Exception raised when a link cannot be broken."""
    def __init__(self, message: str):
        super().__init__(message)


def export(
    folder_path: pathlib.Path,
    file_type: str,
    reference_behaviour: str,
    all_versions: bool
):
    """Export the active design to the specified folder."""
    # Ensure the export folder exists
    _prepare_export_folder(folder_path)

    for design, design_path in _designs_to_export(all_versions):
        # Export the design
        try:
            futil.log(f"Exporting {design_path} (v{design.versionNumber}) to {folder_path}")
            _export_design(design, folder_path, design_path, file_type, reference_behaviour)
        except Exception as e:
            futil.handle_error(f"Failed to export {design_path}: {e}")


def _prepare_export_folder(folder_path: pathlib.Path):
    """Prepare the export folder by creating it if it doesn't exist."""
    folder_path.mkdir(parents=True, exist_ok=True)


def _designs_to_export(all_versions: bool):
    """Get the designs to export."""
    app = adsk.core.Application.get()
    root_folder = app.data.activeProject.rootFolder

    folder_list = [(root_folder, pathlib.Path(""))]
    while folder_list:
        folder, path = folder_list.pop(0)

        # Yield all Fusion designs in the folder
        for item in folder.dataFiles:
            # Skip non-Fusion designs
            if item.fileExtension != "f3d":
                continue

            # Yield all versions of the design
            if all_versions:
                for version in item.versions:
                    final_name = version.name + f"_v{version.versionNumber}"
                    yield (version, path / final_name)
            else:
                final_name = item.name + f"_v{item.versionNumber}"
                yield (item, path / final_name)

        # Add subfolders to the list
        folder_list.extend([(f, path / f.name) for f in folder.dataFolders])


def _export_design(
    data_file: adsk.core.DataFile,
    folder_path: pathlib.Path,
    design_path: pathlib.Path,
    file_type: str,
    reference_behaviour: str
):
    """Export the specified design to the specified folder."""
    # Check if the design references other designs
    if reference_behaviour == "Ignore Design":
        if data_file.hasChildReferences:
            futil.log(f"Ignoring {design_path} because it references other designs")
            return

    # Open design
    design_document = _open_design(data_file)

    try:
        if data_file.hasChildReferences:
            futil.log(f"Breaking references for {design_path}")
            futil.design().activateRootComponent()
            for occ in futil.design().rootComponent.allOccurrences:
                if occ.isReferencedComponent and not occ.breakLink():
                    raise BreakLinkFailure(occ.name)

        # Ensure the export folder exists
        final_path = folder_path / design_path
        final_path.parent.mkdir(parents=True, exist_ok=True)

        # Export the design
        root = futil.design().rootComponent
        options = _export_options(file_type, str(final_path), root)
        futil.design().exportManager.execute(options)
    except BreakLinkFailure as e:
        futil.log(f"Failed to break links for {design_path}: {e}")
    except Exception as e:
        futil.handle_error(f"Failed to export {design_path}: {e}")
    finally:
        design_document.close(False)


def _open_design(data_file: adsk.core.DataFile) -> adsk.core.Document:
    """Open the specified design."""
    (document := futil.app().documents.open(data_file, False)).activate()
    return document


def _export_options(file_type, filename: str, geometry):
    """Get the export options for the specified file type."""
    manager = futil.design().exportManager
    if file_type == "f3d":
        return manager.createFusionArchiveExportOptions(filename, geometry)
    elif file_type == "stl":
        return manager.createSTLExportOptions(geometry, filename)
    elif file_type == "step":
        return manager.createSTEPExportOptions(filename, geometry)
    elif file_type == "obj":
        return manager.createOBJExportOptions(geometry, filename)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
