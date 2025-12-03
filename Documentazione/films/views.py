from django.db.models import Q
from django.views.generic import ListView

from .models import Film


class FilmListView(ListView):
    template_name = 'films/film_list.html'
    model = Film
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().select_related('director').prefetch_related('genres')
        search = self.request.GET.get('q', '').strip()
        watched = self.request.GET.get('watched')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(director__name__icontains=search)
                | Q(genres__name__icontains=search)
            ).distinct()

        if watched == 'yes':
            queryset = queryset.filter(watched=True)
        elif watched == 'no':
            queryset = queryset.filter(watched=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['watched'] = self.request.GET.get('watched', '')
        return context
