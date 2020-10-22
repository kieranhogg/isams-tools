import datetime
import datetime as dt
import json
import logging
from xml.etree import ElementTree

import requests

from isams_tools.connectors.isams import iSAMSConnection
from isams_tools.models import Form, Student, Teacher
from settings import *

logger = logging.getLogger("root")


class APIConnection:
    """Parent class of the connection types, does the generic stuff"""

    data = None
    provides_user_fields = (
        "isams_id",
        "forename",
        "surname",
        "username",
        "email",
        "school_year",
        "form",
    )
    unique_field = "isams_id"

    def __init__(self, url=None, start_date=None, end_date=None):
        self.start_date = start_date
        self.end_date = end_date

    def connect(self, url):
        if DEBUG_DATA:
            logger.debug("Opening data file: " + DEBUG_DATA)
            file = open(DEBUG_DATA, "r")
            self.data = file.read()
        else:
            if DEBUG and DEBUG_START_DATE:
                self.start_date = DEBUG_START_DATE
            else:
                self.start_date = dt.datetime.today().strftime("%Y-%m-%d")

            # OutofSchoolPupils seems to need the endDate to be +1 for it to work correctly
            if DEBUG and DEBUG_END_DATE:
                self.end_date = self.start_date
                end_date_plus_one = (
                    dt.datetime.strptime(DEBUG_END_DATE, "%Y-%m-%d")
                    + dt.timedelta(days=1)
                ).strftime("%Y-%m-%d")
            else:
                self.end_date = self.start_date
                end_date_plus_one = (dt.datetime.strptime(self.start_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

            # as we need to get all data, even if we're not looking at register we still need the filters
            self.filters = """<?xml version='1.0' encoding='utf-8'?>
                    <Filters>
                        <RegistrationManager>
                            <RegistrationStatus startDate="{0}" endDate="{1}" />
                            <OutOfSchoolPupils startDate="{0}" endDate="{2}" />
                        </RegistrationManager>
                    </Filters>
                    """.format(
                self.start_date, self.end_date, end_date_plus_one
            )

            logger.debug("Filters:" + self.filters)
            headers = {"Content-Type": "application/xml"}
            r = requests.post(url, data=self.filters, headers=headers)
            logger.info("Opening connection to: " + url)
            self.data = r.text

    def get_data(self):
        return self.data


class iSAMSJSONConnection(APIConnection):
    """Object to represent a JSON specific connection"""

    data = None
    url = "{0}/api/batch/1.0/json.ashx?apiKey={{{1}}}".format(URL, API_KEY)

    def __init__(self, url=URL, start_date=None, end_date=None):
        logger.debug("Creating JSON connector")
        super().__init__(url, start_date, end_date)

    def connect(self):
        logger.debug("Connecting using JSON connector")
        super().connect(self.url)
        self.data = json.loads(super().get_data())

    def get_student(self, isams_id):
        found_student = None
        students = self.data["iSAMS"]["PupilManager"]["CurrentPupils"]["Pupil"]
        for student in students:
            if student["SchoolId"] == isams_id:
                form = self.get_form_from_name(student["Form"])
                found_student = Student(
                    forename=student["Forename"],
                    surname=student["Surname"],
                    username=student["UserName"],
                    email=student["EmailAddress"],
                    nc_year=student["NCYear"],
                    form=form,
                    date_of_birth=student["DOB"],
                    gender=student["Gender"],
                    sync_value=student["SchoolId"],
                )

        return found_student

    def get_all_students(self):
        raise NotImplementedError

    def get_form_from_name(self, form_name):
        found_form = None

        forms = self.data["iSAMS"]["SchoolManager"]["Forms"]["Form"]
        for form in forms:
            if form["Form"] == form_name:
                teacher = self.get_teacher_from_id(form["@TutorId"])
                found_form = Form(form["Form"], teacher, form["NationalCurriculumYear"])
        return found_form

    def get_teacher_from_id(self, teacher_id):
        found_teacher = None

        teachers = self.data["iSAMS"]["HRManager"]["CurrentStaff"]["StaffMember"]
        for teacher in teachers:
            if teacher["@Id"] == teacher_id:
                found_teacher = Teacher(
                    id=teacher["@Id"],
                    forename=teacher["Forename"],
                    surname=teacher["Surname"],
                    username=teacher["UserName"],
                    email=teacher["SchoolEmailAddress"],
                )

        return found_teacher

    def get_unregistered_students(self):
        unregistered_students = []
        oos_students = self.get_oos_students()

        if "RegistrationStatuses" in self.data["iSAMS"]["RegistrationManager"]:
            register_entries = self.data["iSAMS"]["RegistrationManager"][
                "RegistrationStatuses"
            ]["RegistrationStatus"]
            logger.debug(f"{len(register_entries)} register entries")
            for entry in register_entries:
                if (
                    entry["Registered"] == "0"
                    and "Code" not in entry
                    and entry["PupilId"] not in oos_students
                ):
                    student = self.get_student(entry["PupilId"])
                    if student:
                        unregistered_students.append(student)

        return unregistered_students

    def get_oos_students(self):
        oos_students = []
        if "Pupil" in self.data["iSAMS"]["RegistrationManager"]:
            register_entries = self.data["iSAMS"]["RegistrationManager"]["OutOfSchool"][
                "Pupil"
            ]

            for entry in register_entries:
                oos_students.append(entry["PupilId"])
        return oos_students


class iSAMSXMLConnection(APIConnection):
    """Object to represent an XML specific connection"""

    url = "{0}/api/batch/1.0/xml.ashx?apiKey={{{1}}}".format(URL, API_KEY)
    data = None
    all_students = {}
    unregistered_students = []
    filters = None
    start_date = None
    end_date = None

    def __init__(self, url=URL, start_date=None, end_date=None):
        logger.debug("Creating XML connector")
        super().__init__()

    def connect(self):
        logger.debug("Connecting using XML connector")
        super().connect(self.url)
        self.data = tree = ElementTree.fromstring(super().get_data())

    def get_data(self) -> ElementTree:
        return self.data

    def get_all_students(self):
        if DEBUG:
            print("start: get_all_students()")
        if not self.data:
            logger.critical("Can't get students as no active iSAMS connection")
            sys.exit(1)

        for this_student in self.data.findall("./PupilManager/CurrentPupils")[0]:
            email = ""
            username = ""
            isams_id = str(this_student.find("SchoolId").text)
            forename = str(this_student.find("Forename").text)
            surname = str(this_student.find("Surname").text)
            form = str(this_student.find("Form").text)
            academic_year = str(this_student.find("NCYear").text)
            form = str(self.get_form_from_name(this_student.find("Form").text))
            date_of_birth = str(this_student.find("DOB").text)
            gender = str(this_student.find("Gender").text)

            try:
                username = str(this_student.find("UserName").text)
                email = str(this_student.find("EmailAddress").text)
            except AttributeError:
                pass

            student = Student(
                forename,
                surname,
                username,
                email,
                academic_year,
                form,
                date_of_birth,
                gender,
                isams_id,
            )
            self.all_students[isams_id] = student

        if DEBUG:
            print("end: get_all_students()")
        return self.all_students

    def get_student(self, isams_id, use_all_students=True):
        student = None
        try:
            username = ""
            email = ""

            this_student = self.data.findall(
                "./PupilManager/CurrentPupils/Pupil[SchoolId='{0}']".format(isams_id)
            )[0]
            forename = this_student.find("Forename").text
            surname = this_student.find("Surname").text
            form = this_student.find("Form").text
            academic_year = this_student.find("NCYear").text
            form = self.get_form_from_name(this_student.find("Form").text)
            date_of_birth = this_student.find("DOB")
            gender = this_student.find("Gender")

            try:
                username = this_student.find("UserName").text
                email = this_student.find("EmailAddress").text
            except AttributeError:
                pass

            student = Student(
                forename,
                surname,
                username,
                email,
                academic_year,
                form,
                date_of_birth,
                gender,
                isams_id,
            )

        except (IndexError, AttributeError):
            # student has left
            pass

        return student

    def get_form_from_name(self, form_name):
        form_data = self.data.findall('.//Form/[@Id="' + form_name + '"]')[0]
        tutor_id = form_data.get("TutorId")
        academic_year = form_data.find("NationalCurriculumYear").text
        logging.debug("Looking for tutor with ID {0}".format(tutor_id))

        try:
            tutor_data = self.data.findall('.//StaffMember/[@Id="' + tutor_id + '"]')[0]
            forename = tutor_data.find("Forename").text
            surname = tutor_data.find("Surname").text
            username = tutor_data.find("UserName").text
            email = tutor_data.find("SchoolEmailAddress").text
        except IndexError as e:
            # we have a invalid (e.g. left) tutor which can happen, we have to ignore this
            logging.warning(
                "Error when finding the tutor of form {0}, this needs to be fixed in iSAMS".format(
                    form_data
                )
            )
            logging.warning(str(e))

        tutor = Teacher(tutor_id, forename, surname, username, email)
        form = Form(form_name, tutor, academic_year)

        return form

    def get_unregistered_students(self):
        unregistered_students = []
        for register_entry in self.data.iter("RegistrationStatus"):
            registration_status = int(register_entry.find("Registered").text)
            present_code = None

            try:
                present_code = int(register_entry.find("Code").text)
            except AttributeError:
                pass

            if registration_status == 0 and not present_code:
                isams_id = register_entry.find("PupilId").text
                student = self.get_student(isams_id, False)

                # if we have a student who leaves this can sometimes be None
                if student:
                    unregistered_students.append(student)

        return unregistered_students
