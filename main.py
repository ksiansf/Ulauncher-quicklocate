import subprocess
import os
import shlex
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction


def find_plocate(search, max_results=50):
    """
    Search files using 'plocate' for fast indexed searching.
    Returns a list of paths.
    Includes debug output to ~/.cache/ulauncher.log.
    """
    if not search:
        return []

    # Try to find plocate full path
    plocate_path = "/usr/bin/plocate"
    if not os.path.exists(plocate_path):
        # Try fallback to locate
        plocate_path = "/usr/bin/locate"

    cmd = f'{plocate_path} {shlex.quote(search)}'
    print(f"[QuickLocate DEBUG] Running command: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.stderr:
            print(f"[QuickLocate DEBUG] STDERR: {result.stderr.strip()}")
        if result.returncode != 0:
            print(f"[QuickLocate DEBUG] Command failed with code {result.returncode}")
            return []

        paths = result.stdout.splitlines()
        print(f"[QuickLocate DEBUG] Found {len(paths)} results")
        return paths[:max_results]

    except Exception as e:
        print(f"[QuickLocate ERROR] Exception while running plocate: {e}")
        return []


def get_item(path, name=None, desc=''):
    """Build a Ulauncher result item"""
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
        print(f"[QuickLocate DEBUG] Event triggered: query='{query}', keyword='{keyword}'")

        qf_keyword = extension.preferences.get('qf')
        qdir_keyword = extension.preferences.get('qdir')
        cut_off = int(extension.preferences.get('cut', 10))
        show_dirs = extension.preferences.get('show_dirs', 'yes').lower() == 'yes'

        found = []

        if query:
            if keyword == qf_keyword:
                print("[QuickLocate DEBUG] Performing file search")
                found = find_plocate(query, max_results=cut_off)
            elif keyword == qdir_keyword:
                print("[QuickLocate DEBUG] Performing directory search")
                found = [p for p in find_plocate(query, max_results=cut_off * 2) if os.path.isdir(p)]
                found = found[:cut_off]

        if not found:
            print("[QuickLocate DEBUG] No results found")

        items = []
        for path in found:
            items.append(get_item(path))
            if show_dirs and not path.endswith('/'):
                dir_path = os.path.dirname(path)
                items.append(get_item(dir_path, name=f'↑Dir: {dir_path}', desc='Directory of the file above'))

        return RenderResultListAction(items)


if __name__ == '__main__':
    QuickLocateExtension().run()
