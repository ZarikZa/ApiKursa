from django_filters import rest_framework as filters
from django.db.models import Exists, OuterRef
from .models import Vacancy, Favorites, Applicant

class VacancyFilter(filters.FilterSet):
    city = filters.CharFilter(field_name='city', lookup_expr='icontains')
    category = filters.CharFilter(field_name='category')
    experience = filters.CharFilter(field_name='experience')

    salary_min = filters.NumberFilter(field_name='salary_min', lookup_expr='gte')
    salary_max = filters.NumberFilter(field_name='salary_max', lookup_expr='lte')

    no_experience = filters.BooleanFilter(method='filter_no_experience')
    only_favorites = filters.BooleanFilter(method='filter_only_favorites')

    def filter_no_experience(self, queryset, name, value):
        if value:
            return queryset.filter(experience='Без опыта')
        return queryset

    def filter_only_favorites(self, queryset, name, value):
        request = self.request
        if not value or not request.user.is_authenticated:
            return queryset

        try:
            applicant = request.user.applicant
        except Applicant.DoesNotExist:
            return queryset.none()

        favorites_subquery = Favorites.objects.filter(
            applicant=applicant,
            vacancy=OuterRef('pk')
        )

        return queryset.annotate(
            is_favorite=Exists(favorites_subquery)
        ).filter(is_favorite=True)

    class Meta:
        model = Vacancy
        fields = ['city', 'category', 'experience', 'salary_min', 'salary_max']
