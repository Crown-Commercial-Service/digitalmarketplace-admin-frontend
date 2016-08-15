import unicodecsv


def iter_csv(rows, headers):

    class Line(object):
        def __init__(self):
            self._line = None

        def write(self, line):
            self._line = line

        def read(self):
            return self._line

    rows.insert(0, {header: header for header in headers})

    line = Line()
    writer = unicodecsv.writer(line)
    for row in rows:
        writer.writerow([row.get(header, '') for header in headers])
        yield line.read()
