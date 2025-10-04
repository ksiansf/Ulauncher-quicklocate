import subprocess
import os
import re
import shlex
import shutil
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
MIN_QUERY_LENGTH = 3  

def find_plocate(search, max_results=50):
    """
    Search files using plocate or locate.
    Automatically detects the executable and prints debug info.
    Returns a list of paths.
    """
    if not search:
        return []

    # Auto-detect plocate or locate
    plocate_path = shutil.which("plocate") or shutil.which("locate")
    if not plocate_path:
        print("[QuickLocate ERROR] plocate/locate not found in PATH")
        return []

    print(f"[QuickLocate DEBUG] Using executable: {plocate_path}")

    # Build and run command safely
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
        print(f"[QuickLocate DEBUG] Raw output ({len(paths)} lines): {paths[:10]}")  # first 10 lines
        return paths[:max_results]

    except Exception as e:
        print(f"[QuickLocate ERROR] Exception while running plocate: {e}")
        return []


def get_item(path, name=None, desc=''):
    """Build a Ulauncher result item"""
    return ExtensionResultItem(
        name=name if name else path,
        on_enter=RunScriptAction(f'xdg-open "{path}"', [])
    )

def prioritize_results(paths, query):
    """
    Prioritize search results:
    1. Exact filename match
    2. Whole-word match
    3. Partial (character) match
    """
    query_lower = query.lower()
    exact = []
    word_match = []
    partial = []

    for p in paths:
        filename = os.path.basename(p).lower()

        if filename == query_lower:
            exact.append(p)
        # Use regex to find query as a whole word (word boundaries)
        elif re.search(rf'\b{re.escape(query_lower)}\b', filename):
            word_match.append(p)
        elif query_lower in filename:
            partial.append(p)

    return exact + word_match + partial

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

        
        if query and len(query) >= MIN_QUERY_LENGTH:
            if keyword == qf_keyword:
                print("[QuickLocate DEBUG] Performing file search")
                found = find_plocate(query, max_results=cut_off*2)  # fetch extra for prioritization
                found = prioritize_results(found, query)
                found = found[:cut_off]  # limit final results
            elif keyword == qdir_keyword:
                print("[QuickLocate DEBUG] Performing directory search")
                found = [p for p in find_plocate(query, max_results=cut_off*4) if os.path.isdir(p)]
                found = prioritize_results(found, query)
                found = found[:cut_off]
        else:
            print(f"[QuickLocate DEBUG] Query too short, ignoring: '{query}'")

        if not found:
            print("[QuickLocate DEBUG] No results found")

        items = []
        for path in found:
            items.append(get_item(path))
            # Optionally show parent directory
            if show_dirs and not path.endswith('/'):
                dir_path = os.path.dirname(path)
                items.append(get_item(dir_path, name=f'↑Dir: {dir_path}', desc='Directory of the file above'))

        return RenderResultListAction(items)


if __name__ == '__main__':
    QuickLocateExtension().run()
