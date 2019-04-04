from __future__ import absolute_import, unicode_literals

from django import forms
from django.core.paginator import InvalidPage, Paginator
from django.db import models
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.text import Truncator

from wagtail.contrib.wagtailroutablepage.models import RoutablePageMixin, route
from wagtail.wagtailadmin.edit_handlers import (
    FieldPanel, MultiFieldPanel, ObjectList, StreamFieldPanel, TabbedInterface
)
from wagtail.wagtailcore.fields import RichTextField, StreamField
from wagtail.wagtailcore.models import Page
from wagtail.wagtailsearch import index
from wagtail.wagtailsnippets.edit_handlers import SnippetChooserPanel

from modelcluster.fields import ParentalKey, ParentalManyToManyField
from wagtailautocomplete.edit_handlers import AutocompletePanel

from v1 import blocks as v1_blocks
from v1.atomic_elements import molecules, organisms
from v1.models import (
    CFGOVPage, CFGOVPageManager, LandingPage, PortalCategory, PortalTopic
)
from v1.models.snippets import RelatedResource, ReusableText
from v1.jinja2_environment import environment


REUSABLE_TEXT_TITLES = {
    'about_us': {
        'en': 'About us (For consumers)',
        'es': 'About us (for consumers) (in Spanish)'
    },
    'disclaimer': {
        'en': 'Legal disclaimer for consumer materials',
        'es': 'Legal disclaimer for consumer materials (in Spanish)'
    }
}


def get_standard_text(language, text_type):
    return get_reusable_text_snippet(
        REUSABLE_TEXT_TITLES[text_type][language]
    )


def get_reusable_text_snippet(snippet_title):
    try:
        return ReusableText.objects.get(
            title=snippet_title)
    except ReusableText.DoesNotExist:
        pass


def get_ask_nav_items(request, current_page):
    from ask_cfpb.models import Category
    items = []
    for cat in Category.objects.all():
        if current_page.language == 'es':
            title = cat.name_es
            url = '/es/obtener-respuestas/categoria-{}/'.format(cat.slug_es)
        else:
            title = cat.name
            url = '/ask-cfpb/category-{}/'.format(cat.slug)
        items.append({
            'title': title,
            'url': url,
            'active': False if not hasattr(current_page, 'ask_category')
            else cat.name == current_page.ask_category.name,
            'expanded': True
        })

    return items, True


def get_ask_breadcrumbs(language='en', category=None):
    if language == 'es':
        breadcrumbs = [{
            'title': 'Obtener respuestas', 'href': '/es/obtener-respuestas/'}]
    else:
        breadcrumbs = [{'title': 'Ask CFPB', 'href': '/ask-cfpb/'}]
    if category:
        if language == 'es':
            href = '/es/obtener-respuestas/categoria-{}'.format(
                category.slug_es)
        else:
            href = '/ask-cfpb/category-{}'.format(category.slug)
        breadcrumbs.append({
            'title': category.name_es if language == 'es' else category.name,
            'href': href
        })
    return breadcrumbs


def validate_page_number(request, paginator):
    """
    A utility for parsing a pagination request,
    catching invalid page numbers and always returning
    a valid page number, defaulting to 1.
    """
    raw_page = request.GET.get('page', 1)
    try:
        page_number = int(raw_page)
    except ValueError:
        page_number = 1
    try:
        paginator.page(page_number)
    except InvalidPage:
        page_number = 1
    return page_number


class AnswerLandingPage(LandingPage):
    """
    Page type for Ask CFPB's landing page.
    """
    content_panels = [
        StreamFieldPanel('header')
    ]
    edit_handler = TabbedInterface([
        ObjectList(content_panels, heading='Content'),
        ObjectList(LandingPage.settings_panels, heading='Configuration'),
    ])

    template = 'ask-cfpb/landing-page.html'

    objects = CFGOVPageManager()

    def get_context(self, request, *args, **kwargs):
        from ask_cfpb.models import Category
        context = super(AnswerLandingPage, self).get_context(request)
        context['categories'] = Category.objects.all()
        context['about_us'] = get_standard_text(self.language, 'about_us')
        context['disclaimer'] = get_standard_text(self.language, 'disclaimer')
        return context


class SecondaryNavigationJSMixin(object):
    """A page mixin that adds navigation JS for English pages."""
    @property
    def page_js(self):
        js = super(SecondaryNavigationJSMixin, self).page_js
        if self.language == 'en':
            js += ['secondary-navigation.js']
        return js


class AnswerCategoryPage(RoutablePageMixin, SecondaryNavigationJSMixin,
                         CFGOVPage):
    """
    A routable page type for Ask CFPB category pages and their subcategories.
    """
    from ask_cfpb.models import Answer, Audience, Category, SubCategory

    objects = CFGOVPageManager()
    content = StreamField([], null=True)
    ask_category = models.ForeignKey(
        Category,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='category_page')
    ask_subcategory = models.ForeignKey(
        SubCategory,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='subcategory_page')
    content_panels = CFGOVPage.content_panels + [
        FieldPanel('ask_category', Category),
        StreamFieldPanel('content'),
    ]

    edit_handler = TabbedInterface([
        ObjectList(content_panels, heading='Content'),
        ObjectList(CFGOVPage.settings_panels, heading='Configuration'),
    ])

    template = 'ask-cfpb/category-page.html'

    def get_context(self, request, *args, **kwargs):
        context = super(
            AnswerCategoryPage, self).get_context(request, *args, **kwargs)
        answers = self.ask_category.answerpage_set.filter(
            language=self.language, redirect_to=None, live=True).values(
                'answer_id', 'question', 'slug', 'answer')
        subcats = self.ask_category.subcategories.all()
        context.update({
            'answers': answers,
            'choices': subcats,
            'results_count': answers.count(),
            'get_secondary_nav_items': get_ask_nav_items,
            'breadcrumb_items': get_ask_breadcrumbs(self.language),
            'about_us': get_standard_text(self.language, 'about_us'),
            'disclaimer': get_standard_text(self.language, 'disclaimer'),
            'gettext': environment.func_globals.get('ugettext'),
        })
        return context

    # Returns an image for the page's meta Open Graph tag
    @property
    def meta_image(self):
        return self.ask_category.category_image

    @route(r'^$')
    def category_page(self, request):
        context = self.get_context(request)
        paginator = Paginator(context.get('answers'), 20)
        page_number = validate_page_number(request, paginator)
        page = paginator.page(page_number)
        context.update({
            'paginator': paginator,
            'current_page': page_number,
            'questions': page,
        })

        return TemplateResponse(
            request,
            self.template,
            context)

    @route(r'^(?P<subcat>[^/]+)/$')
    def subcategory_page(self, request, **kwargs):
        subcat = self.SubCategory.objects.filter(
            slug=kwargs.get('subcat')).first()
        if subcat:
            self.ask_subcategory = subcat
        else:
            raise Http404
        context = self.get_context(request)
        answers = self.ask_subcategory.answerpage_set.filter(
            language=self.language)
        paginator = Paginator(answers, 20)
        page_number = validate_page_number(request, paginator)
        page = paginator.page(page_number)
        context.update({
            'paginator': paginator,
            'current_page': page_number,
            'results_count': answers.count(),
            'questions': page,
            'breadcrumb_items': get_ask_breadcrumbs(
                self.language,
                self.ask_category
            )
        })

        return TemplateResponse(
            request, self.template, context)


class AnswerResultsPage(SecondaryNavigationJSMixin, CFGOVPage):

    objects = CFGOVPageManager()
    answers = []

    content = StreamField([
    ], null=True)

    content_panels = CFGOVPage.content_panels + [
        StreamFieldPanel('content'),
    ]

    edit_handler = TabbedInterface([
        ObjectList(content_panels, heading='Content'),
        ObjectList(CFGOVPage.settings_panels, heading='Configuration'),
    ])

    template = 'ask-cfpb/answer-search-results.html'

    def get_context(self, request, **kwargs):
        context = super(
            AnswerResultsPage, self).get_context(request, **kwargs)
        context.update(**kwargs)
        paginator = Paginator(self.answers, 20)
        page_number = validate_page_number(request, paginator)
        page = paginator.page(page_number)
        context['current_page'] = page_number
        context['paginator'] = paginator
        context['results'] = page
        context['results_count'] = len(self.answers)
        context['get_secondary_nav_items'] = get_ask_nav_items
        context['breadcrumb_items'] = get_ask_breadcrumbs(self.language)
        context['about_us'] = get_standard_text(self.language, 'about_us')
        context['disclaimer'] = get_standard_text(self.language, 'disclaimer')
        return context


class TagResultsPage(RoutablePageMixin, AnswerResultsPage):
    """A routable page for serving Answers by tag"""

    template = 'ask-cfpb/answer-search-results.html'

    objects = CFGOVPageManager()

    @route(r'^$')
    def tag_base(self, request):
        raise Http404

    @route(r'^(?P<tag>[^/]+)/$')
    def tag_search(self, request, **kwargs):
        tag = kwargs.get('tag').replace('_', ' ')
        self.answers = [
            (p.url, p.question, p.short_answer if p.short_answer else p.answer)
            for p in AnswerPage.objects.filter(
                search_tags__contains=tag,
                language=self.language,
                live=True,
                redirect_to=None)
        ]
        paginator = Paginator(self.answers, 20)
        page_number = validate_page_number(request, paginator)
        page = paginator.page(page_number)
        context = self.get_context(request)
        context['current_page'] = page_number
        context['results'] = page
        context['results_count'] = len(self.answers)
        context['tag'] = tag
        context['paginator'] = paginator
        return TemplateResponse(
            request,
            self.template,
            context)


class AnswerPage(CFGOVPage):
    """
    Page type for Ask CFPB answers.
    """
    from ask_cfpb.models import Answer
    last_edited = models.DateField(
        blank=True,
        null=True,
        help_text="Change the date to today if you make a significant change.")
    question = models.TextField(blank=True)
    statement = models.TextField(
        blank=True,
        help_text=(
            "(Optional) Use this field to rephrase the question title as "
            "a statement. Use only if this answer has been chosen to appear "
            "on a money topic portal (e.g. /consumer-tools/debt-collection)."))
    short_answer = RichTextField(
        blank=True, help_text='Optional answer intro')
    answer = RichTextField(
        blank=True,
        features=[
            'bold', 'italic', 'h2', 'h3', 'h4', 'link', 'ol', 'ul',
            'document-link', 'image', 'embed', 'ask-tips', 'edit-html'
        ],
        help_text=(
            "Do not use H2 or H3 to style text. Only use the HTML Editor "
            "for troubleshooting. To style tips, warnings and notes, "
            "select the content that will go inside the rule lines "
            "(so, title + paragraph) and click the Pencil button "
            "to style it. Re-select the content and click the button "
            "again to unstyle the tip."
        )
    )
    answer_base = models.ForeignKey(
        Answer,
        blank=True,
        null=True,
        related_name='answer_pages',
        on_delete=models.SET_NULL)
    redirect_to = models.ForeignKey(
        Answer,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='redirected_pages',
        help_text="Choose another Answer to redirect this page to")
    redirect_to_page = models.ForeignKey(
        'self',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='redirect_to_pages',
        help_text="Choose another AnswerPage to redirect this page to")
    featured = models.BooleanField(
        default=False,
        help_text=(
            "Check to make this one of two featured answers "
            "on the landing page."))
    featured_rank = models.IntegerField(blank=True, null=True)
    category = models.ManyToManyField(
        'Category',
        blank=True,
        help_text=(
            "Categorize this answer. "
            "Avoid putting into more than one category."))
    subcategory = models.ManyToManyField(
        'SubCategory',
        blank=True,
        help_text=(
            "Choose only subcategories that belong "
            "to one of the categories checked above."))
    search_tags = models.CharField(
        max_length=1000,
        blank=True,
        help_text="Search words or phrases, separated by commas")
    related_resource = models.ForeignKey(
        RelatedResource,
        blank=True,
        null=True,
        on_delete=models.SET_NULL)
    related_questions = ParentalManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='related_question',
        help_text='Maximum of 3 related questions')
    answer_id = models.IntegerField(default=0)
    portal_topic = ParentalManyToManyField(
        PortalTopic,
        blank=True,
        help_text='Limit to 1 portal topic if possible')
    primary_portal_topic = ParentalKey(
        PortalTopic,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='primary_portal_topic',
        help_text=(
            "Use only if assigning more than one portal topic, "
            "to control which topic is used as a breadcrumb."))
    portal_category = ParentalManyToManyField(
        PortalCategory,
        blank=True)

    user_feedback = StreamField([
        ('feedback', v1_blocks.Feedback()),
    ], blank=True)

    content_panels = CFGOVPage.content_panels + [
        MultiFieldPanel([
            FieldPanel('last_edited'),
            FieldPanel('question'),
            FieldPanel('statement'),
            FieldPanel('short_answer'),
            FieldPanel('answer')],
            heading="Page content",
            classname="collapsible"),
        MultiFieldPanel([
            SnippetChooserPanel('related_resource'),
            AutocompletePanel(
                'related_questions',
                page_type='ask_cfpb.AnswerPage',
                is_single=False)],
            heading="Related resources",
            classname="collapsible"),
        MultiFieldPanel([
            FieldPanel('portal_topic', widget=forms.CheckboxSelectMultiple),
            FieldPanel('primary_portal_topic'),
            FieldPanel(
                'portal_category', widget=forms.CheckboxSelectMultiple)],
            heading="Portal tags",
            classname="collapsible"),
        MultiFieldPanel([
            AutocompletePanel(
                'redirect_to_page', page_type='ask_cfpb.AnswerPage')],
            heading="Redirect to another answer",
            classname="collapsible"),
        MultiFieldPanel([
            StreamFieldPanel('user_feedback')],
            heading="User feedback",
            classname="collapsible collapsed"),
    ]

    sidebar = StreamField([
        ('call_to_action', molecules.CallToAction()),
        ('related_links', molecules.RelatedLinks()),
        ('related_metadata', molecules.RelatedMetadata()),
        ('email_signup', organisms.EmailSignUp()),
        ('sidebar_contact', organisms.SidebarContactInfo()),
        ('rss_feed', molecules.RSSFeed()),
        ('social_media', molecules.SocialMedia()),
        ('reusable_text', v1_blocks.ReusableTextChooserBlock(ReusableText)),
    ], blank=True)

    sidebar_panels = [StreamFieldPanel('sidebar'), ]

    search_fields = Page.search_fields + [
        index.SearchField('answer'),
        index.SearchField('short_answer')
    ]

    edit_handler = TabbedInterface([
        ObjectList(content_panels, heading='Content'),
        ObjectList(sidebar_panels, heading='Sidebar (English only)'),
        ObjectList(CFGOVPage.settings_panels, heading='Configuration'),
    ])

    template = 'ask-cfpb/answer-page.html'

    objects = CFGOVPageManager()

    def get_context(self, request, *args, **kwargs):
        context = super(AnswerPage, self).get_context(request)
        context['related_questions'] = self.related_questions.all()
        context['description'] = self.short_answer if self.short_answer \
            else Truncator(self.answer).words(40, truncate=' ...')
        context['last_edited'] = self.last_edited
        context['category'] = self.category.first()
        context['breadcrumb_items'] = get_ask_breadcrumbs(
            self.language, context['category']
        )
        context['about_us'] = get_standard_text(self.language, 'about_us')
        context['disclaimer'] = get_standard_text(self.language, 'disclaimer')
        context['category'] = self.category.first()
        if self.language == 'en':
            subcategories = []
            for subcat in self.subcategory.all():
                if subcat.parent == context['category']:
                    subcategories.append(subcat)
                for related in subcat.related_subcategories.all():
                    if related.parent == context['category']:
                        subcategories.append(related)
            context['subcategories'] = set(subcategories)

        return context

    def __str__(self):
        if self.answer_base:
            return '{}: {}'.format(self.answer_base.id, self.title)
        else:
            return self.title

    @property
    def clean_search_tags(self):
        return [
            tag.strip()
            for tag in self.search_tags.split(',')
        ]

    @property
    def status_string(self):
        if self.redirect_to_page:
            if not self.live:
                return ("redirected but not live")
            else:
                return ("redirected")
        else:
            return super(AnswerPage, self).status_string

    # Returns an image for the page's meta Open Graph tag
    @property
    def meta_image(self):
        if self.social_sharing_image:
            return self.social_sharing_image

        if not self.category.exists():
            return None

        return self.category.first().category_image

    # Overrides the default of page.id for comparing against split testing
    # clusters. See: core.feature_flags.in_split_testing_cluster
    @property
    def split_test_id(self):
        return self.answer_base.id
