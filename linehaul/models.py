# Copyright 2013 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import StringIO
import uuid
import datetime
import os

from linehaul.tables import downloads


def fmt(n):
    if n is None:
        return "\N"
    elif isinstance(n, datetime.datetime):
        return n.strftime("%Y-%m-%d %H:%M:%S z")
    else:
        return n


class DownloadStatisticsModels(object):
    def __init__(self, engine):
        self._engine = engine
        self._data = []

    def save(self):
        print("Saving!")

        with open("data.txt", "w") as fp:
            fp.write("\n".join(
                "\t".join(fmt(y) for y in x) for x in self._data
            ))

        with self._engine.connect() as conn:
            conn.execute("COPY downloads FROM '%s'" % os.path.join(os.path.abspath("."), "data.txt"))
            conn.execute("COMMIT")


    def create_download(self, package_name, package_version, distribution_type,
                        python_type, python_release, python_version,
                        installer_type, installer_version, operating_system,
                        operating_system_version, download_time,
                        raw_user_agent):
            if installer_type == "ensetuptools":
                installer_type = "setuptools"

            self._data.append([
                str(uuid.uuid4()),
                package_name,
                package_version,
                distribution_type,
                python_type,
                python_release,
                python_version,
                installer_type,
                installer_version,
                operating_system,
                operating_system_version,
                download_time,
                "",
            ])
