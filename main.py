import subprocess
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
import os
import shlex

def find_plocate(search, max_results=50):
    """
    Search files using 'plocate' for fast indexed searching.
    Returns a list of paths.
    """
    if not search:
        return []

    # Safely quote the search term
    cmd = f'plocate {shlex.quote(search)}'

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        paths = result.stdout.splitlines()
        return paths[:max_results]
    except subprocess.CalledProcessError:
        return []  # plocate failed or no results

def get_item(path, name=None, desc=''):
    """
    Build a Ulauncher result item
    """
    return ExtensionResultItem(
        icon='images/icon.png',
        name=name if name else path,
        description=desc,
        on_enter=RunScriptAction(f'xdg-open "{path}"', [])
    )

class QuickLocateExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, QuickLocateEventListener())

class QuickLocateEventListener(EventListener):
    def on_event(self, event, extension):
        query = event.get_argument()
        keyword = event.get_keyword()

        # Read preferences
        fd_keyword = extension.preferences.get('fd')
        fdir_keyword = extension.preferences.get('fdir')
        cut_off = int(extension.preferences.get('cut', 10))
        show_dirs = extension.preferences.get('show_dirs', 'yes').lower() == 'yes'

        found = []

        if query:
            if keyword == fd_keyword:
                found = find_plocate(query, max_results=cut_off)
            elif keyword == fdir_keyword:
                found = [p for p in find_plocate(query, max_results=cut_off*2) if os.path.isdir(p)]
                found = found[:cut_off]

        items = []
        for path in found:
            items.append(get_item(path))
            if show_dirs and not path.endswith('/'):
                dir_path = os.path.dirname(path)
                items.append(get_item(dir_path, name=f'↑Dir: {dir_path}', desc='Directory of the file above'))

        return RenderResultListAction(items)

if __name__ == '__main__':
    QuickLocateExtension().run()
