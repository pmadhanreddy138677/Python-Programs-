def progress_percent(tasks):
    """tasks: any queryset/list of objects with .status. Returns 0-100."""
    tasks = list(tasks)
    if not tasks:
        return 0
    return int(round(100 * sum(1 for t in tasks if t.status == "done") / len(tasks)))


def group_tasks(tasks):
    cols = {"todo": [], "doing": [], "done": []}
    for t in tasks:
        cols[t.status].append(t)
    return cols
