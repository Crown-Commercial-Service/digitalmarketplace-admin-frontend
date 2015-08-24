def label_and_count(stats, groupings):
    return [{
        label: _sum_counts(stats, filters)
        for label, filters in groupings.items()
    }]


def _sum_counts(stats, filter_by=None, sum_by='count'):
    return sum(
        statistic[sum_by] for statistic in stats
        if not filter_by or all(
            statistic.get(key) == value
            for key, value in filter_by.items()
        )
    )
