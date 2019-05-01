from dmutils import csv_generator


def generate_user_csv(users):
    header_row = ("email address", "name")
    user_attributes = ("emailAddress", "name")

    def rows_iter():
        """Iterator yielding header then rows."""
        yield header_row
        for user in sorted(users, key=lambda user: user["name"]):
            yield (user.get(field_name, "") for field_name in user_attributes)

    return csv_generator.iter_csv(rows_iter())
