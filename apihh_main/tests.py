from datetime import date
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Applicant,
    Company,
    Employee,
    Favorites,
    Response,
    StatusResponse,
    StatusVacancies,
    User,
    Vacancy,
    VacancyVideo,
    VacancyVideoLike,
    VacancyVideoView,
    WorkConditions,
)


class ConsoleResultMixin:
    def run(self, result=None):
        if result is None:
            result = self.defaultTestResult()

        before = self._result_counters(result)
        super().run(result)
        after = self._result_counters(result)

        has_failure = (
            after["errors"] > before["errors"]
            or after["failures"] > before["failures"]
            or after["expected_failures"] > before["expected_failures"]
            or after["unexpected_successes"] > before["unexpected_successes"]
        )
        has_skip = after["skipped"] > before["skipped"]

        if has_failure:
            print(f"[FAIL] {self.id()}")
        elif has_skip:
            print(f"[SKIP] {self.id()}")
        else:
            print(f"[PASS] {self.id()}")

        return result

    def _result_counters(self, result):
        return {
            "errors": len(getattr(result, "errors", [])),
            "failures": len(getattr(result, "failures", [])),
            "skipped": len(getattr(result, "skipped", [])),
            "expected_failures": len(getattr(result, "expectedFailures", [])),
            "unexpected_successes": len(getattr(result, "unexpectedSuccesses", [])),
        }


class ApiTestDataMixin:
    def create_user(
        self,
        *,
        email,
        username,
        user_type,
        phone="79990000000",
        password="StrongPass123!",
    ):
        return User.objects.create_user(
            email=email,
            username=username,
            phone=phone,
            password=password,
            user_type=user_type,
        )

    def create_company_user_and_company(
        self,
        *,
        email,
        username,
        company_name="Test Company",
    ):
        user = self.create_user(
            email=email,
            username=username,
            user_type="company",
        )
        company = Company.objects.create(
            user=user,
            name=company_name,
            number="1234567890",
            industry="IT",
            description="Test description",
            verification_document="company_documents/test.pdf",
        )
        return user, company

    def create_applicant_user_and_profile(
        self,
        *,
        email,
        username,
    ):
        user = self.create_user(
            email=email,
            username=username,
            user_type="applicant",
        )
        applicant = Applicant.objects.create(
            user=user,
            first_name="Ivan",
            last_name="Ivanov",
            birth_date=date(1995, 1, 1),
            resume="Resume",
        )
        return user, applicant

    def create_vacancy(self, *, company, position, is_archived=False):
        work_conditions = WorkConditions.objects.create(work_conditions_name="Remote")
        vacancy_status = StatusVacancies.objects.create(status_vacancies_name="Open")
        return Vacancy.objects.create(
            company=company,
            work_conditions=work_conditions,
            position=position,
            description="Vacancy description",
            requirements="Vacancy requirements",
            salary_min="100000.00",
            salary_max="200000.00",
            status=vacancy_status,
            city="Moscow",
            category="IT",
            is_archived=is_archived,
        )

    def extract_items(self, response):
        payload = response.data
        if isinstance(payload, dict) and "results" in payload:
            return payload["results"]
        return payload


class ApiTestCase(ConsoleResultMixin, ApiTestDataMixin, APITestCase):
    pass


class PublicCompanyApiTests(ApiTestCase):
    def test_companies_list_public_for_anonymous(self):
        response = self.client.get("/api/companies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_companies_create_requires_authentication(self):
        response = self.client.post("/api/companies/", data={}, format="json")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_company_me_requires_authentication(self):
        response = self.client.get("/api/company/me/")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


class CompanyCabinetApiTests(ApiTestCase):
    def setUp(self):
        self.owner_user, self.company = self.create_company_user_and_company(
            email="owner@example.com",
            username="owner",
        )
        self.client.force_authenticate(self.owner_user)

    def test_company_me_returns_company_for_owner(self):
        response = self.client.get("/api/company/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.company.id)

    def test_company_me_patch_updates_company_name(self):
        response = self.client.patch(
            "/api/company/me/",
            data={"name": "Updated Company Name"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Updated Company Name")

    def test_company_vacancies_default_excludes_archived(self):
        visible = self.create_vacancy(
            company=self.company,
            position="Visible vacancy",
            is_archived=False,
        )
        archived = self.create_vacancy(
            company=self.company,
            position="Archived vacancy",
            is_archived=True,
        )

        response = self.client.get("/api/company/vacancies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = {item["id"] for item in self.extract_items(response)}
        self.assertIn(visible.id, ids)
        self.assertNotIn(archived.id, ids)

    def test_company_vacancies_archived_query_returns_all(self):
        visible = self.create_vacancy(
            company=self.company,
            position="Visible vacancy",
            is_archived=False,
        )
        archived = self.create_vacancy(
            company=self.company,
            position="Archived vacancy",
            is_archived=True,
        )

        response = self.client.get("/api/company/vacancies/?archived=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ids = {item["id"] for item in self.extract_items(response)}
        self.assertIn(visible.id, ids)
        self.assertIn(archived.id, ids)

    def test_company_vacancy_create_without_company_field(self):
        work_conditions = WorkConditions.objects.create(work_conditions_name="Remote")
        vacancy_status = StatusVacancies.objects.create(status_vacancies_name="Open")
        payload = {
            "work_conditions": work_conditions.id,
            "position": "Backend Developer",
            "description": "Описание вакансии",
            "requirements": "Требования вакансии",
            "salary_min": "120000.00",
            "salary_max": "180000.00",
            "status": vacancy_status.id,
            "city": "Москва",
            "category": "IT",
            "experience": "1-3 года",
            "work_conditions_details": "Удаленная работа",
        }

        response = self.client.post("/api/company/vacancies/", data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["position"], payload["position"])
        self.assertEqual(response.data["company"], self.company.id)


class FavoritesToggleApiTests(ApiTestCase):
    def setUp(self):
        self.applicant_user, self.applicant = self.create_applicant_user_and_profile(
            email="applicant@example.com",
            username="applicant",
        )
        self.company_user, self.company = self.create_company_user_and_company(
            email="company@example.com",
            username="company",
        )
        self.vacancy = self.create_vacancy(
            company=self.company,
            position="Python Developer",
        )

    def test_favorites_toggle_for_non_applicant_forbidden(self):
        self.client.force_authenticate(self.company_user)

        response = self.client.post(
            "/api/favorites/toggle/",
            data={"vacancy": self.vacancy.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            Favorites.objects.filter(
                applicant=self.applicant,
                vacancy=self.vacancy,
            ).exists()
        )

    def test_favorites_toggle_for_applicant_adds_favorite(self):
        self.client.force_authenticate(self.applicant_user)

        response = self.client.post(
            "/api/favorites/toggle/",
            data={"vacancy": self.vacancy.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_favorite"])
        self.assertTrue(
            Favorites.objects.filter(
                applicant=self.applicant,
                vacancy=self.vacancy,
            ).exists()
        )

    def test_favorites_toggle_for_applicant_removes_existing_favorite(self):
        Favorites.objects.create(applicant=self.applicant, vacancy=self.vacancy)
        self.client.force_authenticate(self.applicant_user)

        response = self.client.post(
            "/api/favorites/toggle/",
            data={"vacancy": self.vacancy.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_favorite"])
        self.assertFalse(
            Favorites.objects.filter(
                applicant=self.applicant,
                vacancy=self.vacancy,
            ).exists()
        )


class ApplicantProfileApiTests(ApiTestCase):
    def setUp(self):
        self.applicant_user, self.applicant = self.create_applicant_user_and_profile(
            email="profile_applicant@example.com",
            username="profile_applicant",
        )
        self.client.force_authenticate(self.applicant_user)

    def test_profile_patch_updates_applicant_fields(self):
        response = self.client.patch(
            "/api/user/profile/",
            data={
                "first_name": "Petr",
                "last_name": "Petrov",
                "phone": "+79991112233",
                "birth_date": "1998-05-20",
                "resume": "Updated resume text",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.applicant_user.refresh_from_db()
        self.applicant.refresh_from_db()

        self.assertEqual(self.applicant_user.first_name, "Petr")
        self.assertEqual(self.applicant_user.last_name, "Petrov")
        self.assertEqual(self.applicant_user.phone, "+79991112233")
        self.assertEqual(self.applicant.birth_date.isoformat(), "1998-05-20")
        self.assertEqual(self.applicant.resume, "Updated resume text")
        self.assertEqual(response.data["birth_date"], "1998-05-20")
        self.assertEqual(response.data["resume"], "Updated resume text")

    def test_profile_patch_uploads_applicant_avatar(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color=(32, 64, 192)).save(image_buffer, format="PNG")
        avatar = SimpleUploadedFile("avatar.png", image_buffer.getvalue(), content_type="image/png")

        response = self.client.patch(
            "/api/user/profile/",
            data={"avatar": avatar},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.applicant.refresh_from_db()
        self.assertTrue(bool(self.applicant.avatar))
        self.assertIn("applicant_avatars/", self.applicant.avatar.name)
        self.assertTrue(response.data.get("avatar"))


class ContentManagerProfileApiTests(ApiTestCase):
    def setUp(self):
        self.owner_user, self.company = self.create_company_user_and_company(
            email="owner_cm@example.com",
            username="owner_cm",
            company_name="CM Test Company",
        )

        self.cm_user = self.create_user(
            email="cm@example.com",
            username="cm_user",
            user_type="staff",
            password="OldStrongPass123!",
        )
        self.employee = Employee.objects.create(
            user=self.cm_user,
            company=self.company,
            role="content_manager",
        )

        self.vacancy_1 = self.create_vacancy(
            company=self.company,
            position="CM Vacancy 1",
        )
        self.vacancy_2 = self.create_vacancy(
            company=self.company,
            position="CM Vacancy 2",
        )

        self.status_response = StatusResponse.objects.create(status_response_name="Отправлен")
        self.applicant_user, self.applicant = self.create_applicant_user_and_profile(
            email="cm_applicant@example.com",
            username="cm_applicant",
        )
        Response.objects.create(
            applicants=self.applicant,
            vacancy=self.vacancy_1,
            status=self.status_response,
        )
        Response.objects.create(
            applicants=self.applicant,
            vacancy=self.vacancy_2,
            status=self.status_response,
        )

        sample_video = SimpleUploadedFile("sample.mp4", b"fake-video-content", content_type="video/mp4")
        self.video = VacancyVideo.objects.create(
            vacancy=self.vacancy_1,
            uploaded_by=self.employee,
            company=self.company,
            video=sample_video,
            description="Demo video",
        )
        VacancyVideoView.objects.create(applicant=self.applicant, video=self.video)
        VacancyVideoLike.objects.create(applicant=self.applicant, video=self.video)

    def test_user_profile_contains_company_fields_for_content_manager(self):
        self.client.force_authenticate(self.cm_user)
        response = self.client.get("/api/user/profile/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["employee_role"], "content_manager")
        self.assertEqual(response.data["company_name"], self.company.name)
        self.assertEqual(response.data["company_industry"], self.company.industry)

    def test_change_password_updates_credentials(self):
        self.client.force_authenticate(self.cm_user)
        response = self.client.post(
            "/api/user/change-password/",
            data={
                "old_password": "OldStrongPass123!",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cm_user.refresh_from_db()
        self.assertTrue(self.cm_user.check_password("NewStrongPass123!"))

    def test_change_password_rejects_wrong_old_password(self):
        self.client.force_authenticate(self.cm_user)
        response = self.client.post(
            "/api/user/change-password/",
            data={
                "old_password": "WrongOldPass123!",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_content_manager_stats_returns_expected_payload(self):
        self.client.force_authenticate(self.cm_user)
        response = self.client.get("/api/content-manager/profile/stats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["manager"]["role"], "content_manager")
        self.assertEqual(response.data["company"]["name"], self.company.name)
        self.assertEqual(response.data["stats"]["videos_count"], 1)
        self.assertEqual(response.data["stats"]["vacancies_count"], 2)
        self.assertEqual(response.data["stats"]["responses_count"], 2)
        self.assertIn("labels", response.data["chart"])
        self.assertIn("values", response.data["chart"])

    def test_content_manager_stats_pdf_returns_pdf_file(self):
        self.client.force_authenticate(self.cm_user)
        response = self.client.get("/api/content-manager/profile/stats/pdf/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])

    def test_content_manager_stats_for_non_cm_forbidden(self):
        self.client.force_authenticate(self.applicant_user)
        response = self.client.get("/api/content-manager/profile/stats/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FeedVideoApiTests(ApiTestCase):
    def setUp(self):
        self.owner_user, self.company = self.create_company_user_and_company(
            email="feed_owner@example.com",
            username="feed_owner",
            company_name="Feed Test Company",
        )
        self.cm_user = self.create_user(
            email="feed_cm@example.com",
            username="feed_cm",
            user_type="staff",
        )
        self.employee = Employee.objects.create(
            user=self.cm_user,
            company=self.company,
            role="content_manager",
        )
        self.vacancy = self.create_vacancy(company=self.company, position="Feed vacancy")

        self.applicant_user, self.applicant = self.create_applicant_user_and_profile(
            email="feed_applicant@example.com",
            username="feed_applicant",
        )
        sent_status = StatusResponse.objects.create(status_response_name="Отправлен")
        Response.objects.create(
            applicants=self.applicant,
            vacancy=self.vacancy,
            status=sent_status,
        )

        sample_video = SimpleUploadedFile("feed.mp4", b"feed-video-content", content_type="video/mp4")
        self.video = VacancyVideo.objects.create(
            vacancy=self.vacancy,
            uploaded_by=self.employee,
            company=self.company,
            video=sample_video,
            description="Feed video",
            is_active=True,
        )

    def test_recommended_feed_returns_has_applied_inside_vacancy(self):
        self.client.force_authenticate(self.applicant_user)
        response = self.client.get("/api/feed/videos/recommended/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self.extract_items(response)
        self.assertTrue(items)
        self.assertIn("vacancy", items[0])
        self.assertIn("has_applied", items[0]["vacancy"])
        self.assertTrue(items[0]["vacancy"]["has_applied"])
