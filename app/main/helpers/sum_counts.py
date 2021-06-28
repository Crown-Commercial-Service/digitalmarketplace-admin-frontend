from datetime import datetime


def format_metrics(metrics):
    output = []
    dates = set()
    for metric in metrics:
        for val in metrics[metric]:
            dates.add(val['ts'])

    for date in sorted(list(dates)):
        result = {'created_at': date}
        for metric in metrics:
            for val in metrics[metric]:
                if val['ts'] == date:
                    result[metric] = val['value']
        output.append(result)

    return output


def format_snapshots(snapshots, category, groupings):
    return [
        _label_and_count(
            snapshot['data'][category], groupings, snapshot['createdAt']
        )
        for snapshot in snapshots
    ]


def _label_and_count(stats, groupings, created_at):
    data = {
        label: _sum_counts(stats, filters)
        for label, filters in list(groupings.items())
    }
    data['created_at'] = created_at
    return data


def _sum_counts(stats, filter_by=None, sum_by='count'):
    return sum(
        statistic[sum_by] for statistic in stats
        if not filter_by or all(
            _find(statistic.get(key), value)
            for key, value in list(filter_by.items())
        )
    )


def _find(statistic, filter_value):
    if isinstance(filter_value, list):
        return statistic in filter_value
    else:
        return statistic == filter_value
