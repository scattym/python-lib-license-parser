import logging
import re
import base64
logger = logging.getLogger(__name__)


def check_full_read(data):
    # print(ord(data[0]))
    # print(ord(data[-1]))
    if ord(data[0]) == ord('%') and ord(data[-1]) == ord('?'):
        return True

    # For card reader that does not send start tx and end tx
    if ord(data[0]) == 0x25 and ord(data[-1]) == 0x0A:
        return True
    return False

# print check_iso7811(payload)
# print len(payload)
# data = payload[1:-1]
# print len(data)
# tracks = data.split('?')


def is_cr1300(data):
    if ord(data[0]) == 2:
        return True
    return False


def is_msr100(data):
    if ord(data[0]) == 0x25 and ord(data[-1]) == 0x0A:
        return True
    return False


class License(object):
    def __init__(self, payload=None):
        self.fields = {}
        self.track_1 = None
        self.track_2 = None
        self.track_3 = None
        if payload:
            self.parse_card_read(payload)

    def set_field(self, name, value):
        cleaned = value.rstrip()
        if cleaned and cleaned != "" and self.fields.get(name) is None:
            self.fields[name] = cleaned
            if name == "pan":
                pan_1 = cleaned[0:6]
                id_number = cleaned[6:]
                self.set_field("pan_1", pan_1)
                self.set_field("id_number", id_number)

    def get_field(self, name):
        return self.fields.get(name)

    def parse_pan_unknown_license_unknown(self, payload):
        space_delimited = re.sub(' +', ' ', payload)
        space_delimited = space_delimited.lstrip().rstrip()
        fields = space_delimited.split(' ')
        if len(fields) == 4:
            # self.set_field("id_number", "%s%s%s" % (fields[0:3]))
            self.set_field("license_number", fields[2])
        else:
            logger.error("Field size does not match. Expecting %s but got %s. Ignoring", 4, len(fields))

    def parse_track_1(self, payload):
        self.track_1 = payload
        if '^' in payload:
            fields = payload.split('^')
            logger.debug("Track 1 field length %s" % len(fields))
            if len(fields) != 4:
                logger.error("Unable to properly parse track 1: %s", payload)

            if len(fields) >= 1:
                self.set_field("track1_field0", fields[0])
                self.set_field("pan", fields[0])
            if len(fields) >= 2:
                self.set_field("track1_field1", fields[1])
                if "M" in fields[1]:
                    self.set_field("name", fields[1])
                else:
                    logger.error("Trying to set name, but no M in string %s", fields[1])
                    logger.error("Could be license number. Trying to extract.")
                    self.parse_pan_unknown_license_unknown(payload)
            if len(fields) >= 3:
                self.set_field("track1_field2", fields[2])
                self.set_field("expiration_date_sc_disc", fields[2])
            if len(fields) >= 4:
                self.set_field("track1_field3", fields[3])
                self.set_field("end", fields[3])
        else:
            name = payload.lstrip().rstrip()
            if "M" in name:
                self.set_field("name", name)
            else:
                # We could have a track 1 with license number
                # self.parse_track_3(payload)
                logger.error("Trying to set name, but no M in string %s", name)
                logger.error("Could be license number. Trying to extract.")
                self.parse_pan_unknown_license_unknown(payload)

    def parse_track_2(self, payload):
        self.track_2 = payload

        fields = payload.split('=')
        logger.debug("Track 2 field length %s" % len(fields))
        if len(fields) != 3:
            logger.error("Unable to properly parse track 2: %s", payload)
        if len(fields) >= 1:
            self.set_field("track2_field0", fields[0])
            pan = fields[0]
            self.set_field("pan", pan)
        if len(fields) >= 2:
            expiration_date_sc_disc = fields[1]
            self.set_field("track2_field1", fields[1])
            expiration_date = expiration_date_sc_disc[0:4]
            date_of_birth = expiration_date_sc_disc[4:]
            self.set_field("expiration_date", expiration_date)
            self.set_field("date_of_birth", date_of_birth)

        if len(fields) >= 3:
            end = fields[2]
            self.set_field("track2_field2", fields[2])

    def parse_track_3(self, payload):
        self.track_3 = payload

        space_delimited = re.sub(' +', ' ', payload)
        fields = space_delimited.split(' ')
        if len(fields) != 6:
            if '^' in space_delimited:
                space_delimited = space_delimited.lstrip()
                self.set_field("name", space_delimited.split('^')[1])
                # print("----------------------------------- %s" % space_delimited.split('^')[1])
                logger.info("Fell back to parsing name from track 3")
                return

        logger.debug("Track 3 field length %s" % len(fields))
        if len(fields) != 6 and len(fields) != 5:
            logger.error("Unable to properly parse track 3: %s", payload)

        if len(fields) >= 1:
            field_1 = fields[0]
            self.set_field("track3_field_0", fields[0])
        if len(fields) >= 2:
            field_2 = fields[1]
            self.set_field("track3_field_1", fields[1])
        if len(fields) >= 3:
            license_number = fields[2]
            self.set_field("track3_field_2", fields[2])
            self.set_field("license_number", fields[3])
        if len(fields) >= 4:
            field_4 = fields[3]
            self.set_field("track3_field_3", fields[2])
        if len(fields) >= 5:
            self.set_field("track3_field_4", fields[4])
        if len(fields) >= 6:
            self.set_field("track3_field_5", fields[5])

    def parse_card_read(self, payload):
        if not check_full_read(payload):
            logger.error("Not a full card read payload")
        else:
            if is_cr1300(payload):
                data = payload[1:-1]
            elif is_msr100(payload):
                data = payload[0:-1]
            else:
                data = payload
            tracks = data.split('?')
            logger.debug("Track list is %s", tracks)
            for track in tracks:
                logger.debug("Track is %s", track)
                if len(track) > 0:
                    logger.debug("Track first byte is %s", track[0])
                    if track[0] == '%':  # track 1
                        self.parse_track_1(track[1:])
                    if track[0] == ';':  # track 2
                        self.parse_track_2(track[1:])
                    if track[0] == '+':  # track 3
                        self.parse_track_3(track[1:])

    def __str__(self):
        return "%s %s %s\n%s\n%s\n%s" % (
            self.get_field("license_number"),
            self.get_field("name"),
            self.fields,
            self.track_1,
            self.track_2,
            self.track_3,
        )

    def get_fields(self):
        return self.fields

    def get_expiration_date(self):
        exp_date = self.get_field('expiration_date')
        if exp_date:
            if exp_date == '9999':
                return '999912'
            else:
                return '20%s%s' % (exp_date[0:2], exp_date[2:4])


def parse_card_reader_data(data, line_delim='|'):
    return_dict = {}
    # |+CBC: 0,100,4.230V||OK|
    logger.info(data)
    try:
        payload = base64.b64decode(data["card_read"])

        license = License(payload)
        logger.debug("Return license is: %s" % (license,))
        return license
    except Exception as err:
        if data.get("card_read"):
            logger.error("Unable to parse payload: %s", base64.b64decode(data["card_read"]))
        else:
            logger.error("No card read to parse in payload: %s", data)

    return None


if __name__ == '__main__':
    logger = logging.getLogger('')
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    import pprint
    pp = pprint.PrettyPrinter(indent=4)

    # No name in track 1
    # 0000000 002   %                                                       3
    # 0000020   3   0   0                                                   1
    # 0000040                                                   5   2   0   0
    # 0000060   1   2   7   8           0   0   1   0   4
    # 0000100
    # 0000120   ?   ;   6   0   0   7   6   4   3   2   5   0   9   0   0   0
    # 0000140   0   1   8   1   2   =   9   9   9   9   1   9   7   4   0   8
    # 0000160   2   4   =   ?   +           ^   U   E   A   K   A   N   $   M
    # 0000200   O   N   T   R   I   $   M   R   .   ^   ^   ?  \r 003
    # 0000216

    # Name in track 1, not in track 3
    # 0000000 002   %           ^   S   A   N   T   I   W   O   N   G       S
    # 0000020   U   V   I   N   A   I       M   R   .   ^   ^   ?   ;   6   0
    # 0000040   0   7   6   4   3   1   0   0   4   0   0   4   6   1   1   5
    # 0000060   7   =   9   9   9   9   1   9   7   4   1   0   2   5   =   ?
    # 0000100   +                                                       3   1
    # 0000120   0   0                                                   1
    # 0000140                                               5   8   0   0   3
    # 0000160   1   6   3           0   0   1   0   1
    # 0000200                                                               ?
    # 0000220  \r 003
    # 0000222

    tests = [
        {
            'data': 'AiUgIF5TQU5USVdPTkcgU1VWSU5BSSBNUi5eXj87NjAwNzY0MzEwMDQwMDQ2MTE1Nz05OTk5MTk3NDEwMjU9PysgICAgICAgICAgICAgMzEwMCAgICAgICAgICAgIDEgICAgICAgICAgICA1ODAwMzE2MyAgMDAxMDEgICAgICAgICAgICAgICAgICAgICA/DQM=',
            'name': 'SANTIWONG SUVINAI MR.',
            'id_number': '3100400461157',
            'expiration_date': '9999',
            'date_of_birth': '19741025',
            'license_number': '58003163',
        },
        {
            'data': 'AiUgVEFOVElNRVRIQU5PTiBSSU5SREVFIE1JU1MgPzs2MDA3NjQzMTEwMTAxOTQ0MDgzPTIwMTIxOTc5MTIxNT0/Kz8NAw==',
            'name': 'TANTIMETHANON RINRDEE MISS',
            'id_number': '3110101944083',
            'expiration_date': '2012',
            'date_of_birth': '19791215',
            'license_number': None,
        },
        {
            'data': 'JTFeTUFUVEhFVyBDTEFSSyAgICAgICAgICAgICAgICAgXjExNzI1NzUxICBeODlGREVCQzM4RTRGOTNDRTAxNTY0NzlBQzJFRTE5Njg/Oz0yODE5NDkyMz0yMDQwNjU5MzAwPw0K',  # Matt C license
            'name': 'MATTHEW CLARK',
            'id_number': None,
            'expiration_date': '2819',
            'date_of_birth': '4923',
            'license_number': None,
        },
        {
            'data': 'Ajs2MDA3NjQzMjUwOTAwMDAxODEyPTk5OTkxOTc0MDgyND0/DQM=',    # short read
            'name': None,
            'id_number': '3250900001812',
            'expiration_date': '9999',
            'date_of_birth': '19740824',
            'license_number': None,
        },
        {
            'data': 'AiUgICAgICAgICAgICAgMzMwMCAgICAgICAgICAgIDEgICAgICAgICAgICA1MjAwMTI3OCAgMDAxMDQgICAgICAgICAgICAgICAgICAgICA/OzYwMDc2NDMyNTA5MDAwMDE4MTI9OTk5OTE5NzQwODI0PT8rICBeVUVBS0FOJE1PTlRSSSRNUi5eXj8NAw==',
            'name': 'UEAKAN$MONTRI$MR.',
            'id_number': '3250900001812',
            'expiration_date': '9999',
            'date_of_birth': '19740824',
            'license_number': '52001278',
        },
        {
            'data': 'AiUgICAgICAgICAgICAgMzEwMCAgICAgICAgICAgIDEgICAgICAgICAgICA1MjAwMjY4MiAgMDAxMDQgICAgICAgICAgICAgICAgICAgICA/OzYwMDc2NDMyNTA5MDAwMDE4MTI9OTk5OTE5NzQwODI0PT8NAw==',  # short read
            'name': None,
            'id_number': '3250900001812',
            'expiration_date': '9999',
            'date_of_birth': '19740824',
            'license_number': '52002682',
        },
        {
            'data': 'AiUgIF5ZQU5BSkFSRUUkTklSVVQkTVIuXl4/OzYwMDc2NDMxMDA0OTAwMDAzNzU9OTk5OTE5NjkwNDI2PT8rPw0D',
            'name': 'YANAJAREE$NIRUT$MR.',
            'id_number': '3100490000375',
            'expiration_date': '9999',
            'date_of_birth': '19690426',
            'license_number': None,
        },
        {
            'data': 'AiUgICAgICAgICAgICAgMzEwMCAgICAgICAgICAgIDEgICAgICAgICAgICA1MjAwMjY4MiAgMDAxMDQgICAgICAgICAgICAgICAgICAgICA/OzYwMDc2NDMyNTA5MDAwMDE4MTI9OTk5OTE5NzQwODI0PT8rICBeVUVBS0FOJE1PTlRSSSRNUi5eXj8NAw==',
            'name': 'UEAKAN$MONTRI$MR.',
            'id_number': '3250900001812',
            'expiration_date': '9999',
            'date_of_birth': '19740824',
            'license_number': '52002682',  # #### Bad that these are different
        },
        {
            'data': 'AiUgICAgICAgICAgICAgMzMwMCAgICAgICAgICAgIDEgICAgICAgICAgICA1MjAwMTI3OCAgMDAxMDQgICAgICAgICAgICAgICAgICAgICA/OzYwMDc2NDMyNTA5MDAwMDE4MTI9OTk5OTE5NzQwODI0PT8rICBeVUVBS0FOJE1PTlRSSSRNUi5eXj8NAw==',
            'name': 'UEAKAN$MONTRI$MR.',
            'id_number': '3250900001812',
            'expiration_date': '9999',
            'date_of_birth': '19740824',
            'license_number': '52001278',  # #### Bad that these are different
        },
        {
            'data': 'AiUgIF5KVU5QVUVOR1NPT0skVEhPTkdDSEFJJE1SLl5ePysgICAgICAgICAgICAgMTEwMCAgICAgICAgICAgIDEgICAgICAgICAgICA1OTAwMjY3NCAgNjAzMDAgICAgICAgICAgICAgICAgICAgICA/DQM=',
            'name': 'JUNPUENGSOOK$THONGCHAI$MR.',
            'id_number': None,
            'expiration_date': None,
            'date_of_birth': None,
            'license_number': '59002674',
        },
        {
            'data': 'AiUgIF5QQVlPT00kVEVFUkFTQUskTVIuXl4/OzYwMDc2NDM4MDAzMDAyNzM0OTI9MjIwNTE5NzIwNTAxPT8rICAgICAgICAgICAgIDI2MDAgICAgICAgICAgICAxICAgICAgICAgICAgNTkwMDM5NzIgIDAwMTA0ICAgICAgICAgICAgICAgICAgICAgPw0D',
            'name': 'PAYOOM$TEERASAK$MR.',
            'id_number': '3800300273492',
            'expiration_date': '2205',
            'date_of_birth': '19720501',
            'license_number': '59003972',
        },
        {
            'data': 'AiUgIF5SQURST0dTQSRSVUVOR1lPUyRNUi5eXj87NjAwNzY0MzIxOTkwMDE4ODM5Mj0xODExMTk3NzA5MTY9PysgICAgICAgICAgICAgMTEwMCAgICAgICAgICAgIDEgICAgICAgICAgICA1OTAxMTU3MyAgMDAxMDMgICAgICAgICAgICAgICAgICAgICA/DQM=',
            'name': 'RADROGSA$RUENGYOS$MR.',
            'id_number': '3219900188392',
            'expiration_date': '1811',
            'date_of_birth': '19770916',
            'license_number': '59011573',
        },
        {
            'data': 'AiUgIF5ZQU5BSkFSRUUkSEFUQUlUSVAkTUlTU15ePw0D',
            'name': 'YANAJAREE$HATAITIP$MISS',
            'id_number': None,
            'expiration_date': None,
            'date_of_birth': None,
            'license_number': None,
        },
        {
            'data': 'AiUgIF5ZQU5BSkFSRUUkSEFUQUlUSVAkTUlTU15ePzs2MDA3NjQzMTAwNDAwNzYzMjM0PTk5OTkxOTY1MTIxMD0/KyAgICAgICAgICAgICAzMTAwICAgICAgICAgICAgMiAgICAgICAgICAgIDMzMDAwOTM2ICAwMDEwMyAgICAgICAgICAgICAgICAgICAgID8NAw==',
            'name': 'YANAJAREE$HATAITIP$MISS',
            'id_number': '3100400763234',
            'expiration_date': '9999',
            'date_of_birth': '19651210',
            'license_number': '33000936',
        },
        {
            'data': 'AiUgIF5ZQU5BSkFSRUUkTklSVVQkTVIuXl4/OzYwMDc2NDMxMDA0OTAwMDAzNzU9OTk5OTE5NjkwNDI2PT8rPw0D',
            'name': 'YANAJAREE$NIRUT$MR.',
            'id_number': '3100490000375',
            'expiration_date': '9999',
            'date_of_birth': '19690426',
            'license_number': None,
        },
        {
            'data': 'AiUgU0lIQUJPUkFOIEFOVUNISVQgTVIgPzs2MDA3NjQxNDU5OTAwMDc1OTQ4PTIwMTAxOTg2MTAwNT0/KyAgICAgICAgICAgICAyNDAwICAgICAgICAgICAgMSAgICAgICAgICAgIDU4MDExNDIwICAwMDEwMCAgICAgICAgICAgICAgICAgICAgID8NAw==',
            'name': 'SIHABORAN ANUCHIT MR',
            'id_number': '1459900075948',
            'expiration_date': '2010',
            'date_of_birth': '19861005',
            'license_number': '58011420',
        },
        {
            'data': 'Ajs2MDA3NjQzMjUwOTAwMDAxODEyPTk5OTkxOTc0MDgyND0/DQM=',
            'name': None,
            'id_number': '3250900001812',
            'expiration_date': '9999',
            'date_of_birth': '19740824',
            'license_number': None,
        },
    ]

    test_number = 0
    for test in tests:
        test_data = {}
        test_data['card_read'] = test["data"]
        test_license = parse_card_reader_data(test_data)

        for key in test:
            if key != "data":
                if test[key] is None and test_license.get_field(key) is not None:
                    logger.error(
                        "Test %s. Failed test. Looking for key %s with data %s, but got %s",
                        test_number,
                        key,
                        test[key],
                        test_license.get_field(key)
                    )
                elif test[key] != test_license.get_field(key):
                    logger.error(
                        "Test %s. Failed test. Looking for key %s with data %s, but got %s",
                        test_number,
                        key,
                        test[key],
                        test_license.get_field(key)
                    )
        test_number = test_number + 1

            # print(test_license.get_field('name'))
            # print(test_license.get_field('license_number'))
            # print(test_license.get_field('pan'))
            # print(test_license)
            # print(test_license.get_expiration_date())
            # print(test_license.track_1)
            # print(test_license.track_2)
            # print(test_license.track_3)
            # pp.pprint(test_license.get_fields())
