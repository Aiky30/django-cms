from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _

from cms.api import add_plugin, create_page, create_title
from cms.forms.wizards import CreateCMSPageForm
from cms.models import Page, Placeholder, UserSettings
from cms.test_utils.testcases import (
    CMSTestCase, URL_CMS_PAGE_MOVE,
    URL_CMS_PAGE_CHANGE, URL_CMS_PAGE_ADD,
)
from cms.utils import get_current_site
from cms.wizards.forms import step2_form_factory, WizardStep2BaseForm

# Snippet to create wizard page taken from: test_wizards.py
CreateCMSPageForm = step2_form_factory(
    mixin_cls=WizardStep2BaseForm,
    entry_form_class=CreateCMSPageForm,
)


class LogPageOperationsTests(CMSTestCase):

    def setUp(self):
        self._admin_user = self.get_superuser()

    def _assert_log_created_on_page_add(self, page):
        # Check to see if the page added log entry exists
        self.assertEqual(1, LogEntry.objects.count())

        log_entry = LogEntry.objects.all()[0]
        # Check that the contents of the log message is correct
        self.assertEqual('Added Page Translation', log_entry.change_message)
        # Check the action flag is set correctly
        self.assertEqual(ADDITION, log_entry.action_flag)
        # Check the object id is set correctly
        self.assertEqual(str(page.pk), log_entry.object_id)
        # Check the object_repr is set correctly
        self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_create_admin_page(self):
        """
        When a page is created using the page admin a log entry is created.
        """
        page_data = self.get_new_page_data()

        with self.login_user_context(self._admin_user):
            response = self.client.post(URL_CMS_PAGE_ADD, page_data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 302)
            page_one = Page.objects.get(title_set__slug=page_data['slug'], publisher_is_draft=True)
            self._assert_log_created_on_page_add(page_one)

    def test_log_for_create_wizard_page(self):
        """
        When a page is created via the create page wizard a log entry is created.
        """
        with self.login_user_context(self._admin_user):
            request = self.get_request()

        site = get_current_site()
        data = {
            'title': 'page 1',
            'slug': 'page_1',
            'page_type': None,
        }
        form = CreateCMSPageForm(
            data=data,
            wizard_page=None,
            wizard_site=site,
            wizard_language='en',
            wizard_request=request,
        )

        self.assertTrue(form.is_valid())
        page = form.save()
        self._assert_log_created_on_page_add(page)

    def test_log_for_create_api_page(self):
        """
        When a page is created via the create page api a log entry is NOT created.
        It may help determine why other tests might fail if the api started creating a log for page creation!!
        """
        # Create a page
        create_page('home', 'nav_playground.html', 'en', published=True)
        # Check to see if any logs exist, none should exist
        self.assertEqual(0, LogEntry.objects.count())

    def test_log_for_change_admin_page(self):
        """
        When a page is edited a log entry is created.
        """
        with self.login_user_context(self._admin_user):
            page = create_page('home', 'nav_playground.html', 'en', published=True)
            page_data = self.get_new_page_data()

            # Get and edit the page
            page_data['slug'] = 'changed slug'
            response = self.client.post(URL_CMS_PAGE_CHANGE % page.id, page_data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 302)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual('Changed', log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_move_admin_page(self):
        """
        When a page is moved a log entry is created.
        """
        with self.login_user_context(self._admin_user):
            create_page("page_home", "nav_playground.html", "en", published=False)
            page_1 = create_page("page_a", "nav_playground.html", "en", published=False)
            page_2 = create_page("page_b", "nav_playground.html", "en", published=False)

            # move pages
            response = self.client.post(URL_CMS_PAGE_MOVE % page_2.pk, {"target": page_1.pk, "position": "0"})
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Moved"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page_2.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page_2), log_entry.object_repr)

    def test_log_for_delete_admin_page(self):
        """
        When a page is deleted a log entry is created.
        """
        with self.login_user_context(self._admin_user):
            page = create_page("page_a", "nav_playground.html", "en", published=False)
            pre_deleted_page_id = str(page.pk)
            pre_deleted_page = str(page)
            endpoint = self.get_admin_url(Page, 'delete', page.pk)
            post_data = {'post': 'yes'}

            response = self.client.post(endpoint, post_data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 302)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Deleted"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(DELETION, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(pre_deleted_page_id, log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(pre_deleted_page, log_entry.object_repr)

    def test_log_for_change_translation(self):
        """
        When a pages translation is changed a log entry is created.
        """
        with self.login_user_context(self._admin_user):
            page = create_page("page_a", "nav_playground.html", "en", published=False)
            title = create_title(language='de', title="other title %s" % page.get_title('en'), page=page)
            endpoint = self.get_admin_url(Page, 'edit_title_fields', page.pk, title.language)
            data = model_to_dict(title, fields=['title'])
            data['title'] = 'my_new_title_field'

            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Changed Page Translation"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_delete_translation(self):
        """
        When a pages translation is deleted a log entry is created.
        """
        with self.login_user_context(self._admin_user):
            page = create_page("page_a", "nav_playground.html", "en", published=False)
            create_title(language='de', title="other title %s" % page.get_title('en'), page=page)
            endpoint = self.get_admin_url(Page, 'delete_translation', page.pk)
            post_data = {'post': 'yes', 'language': 'de'}

            response = self.client.post(endpoint, post_data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 302)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Deleted Page Translation"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)


class LogPlaceholderOperationsTests(CMSTestCase):

    def setUp(self):
        self._admin_user = self.get_superuser()
        self._cms_page = self.create_homepage(
            "home",
            "nav_playground.html",
            "en",
            created_by=self._admin_user,
            published=True,
        )
        self._placeholder_1 = self._cms_page.placeholders.get(slot='body')
        self._placeholder_2 = self._cms_page.placeholders.get(slot='right-column')

    def _add_plugin(self, placeholder=None, plugin_type='LinkPlugin', language='en'):
        placeholder = placeholder or self._placeholder_1
        plugin_data = {
            'LinkPlugin': {'name': 'A Link', 'external_link': 'https://www.django-cms.org'},
            'PlaceholderPlugin': {},
        }
        plugin = add_plugin(
            placeholder,
            plugin_type,
            language,
            **plugin_data[plugin_type]
        )
        return plugin

    def _get_add_plugin_uri(self, language='en'):
        uri = self.get_add_plugin_uri(
            placeholder=self._placeholder_1,
            plugin_type='LinkPlugin',
            language=language,
        )
        return uri

    def test_log_for_add_plugin(self):
        """
        When a plugin is created a log entry is created.
        """
        endpoint = self._get_add_plugin_uri()
        data = {'name': 'A Link', 'external_link': 'https://www.django-cms.org'}
        page = self._placeholder_1.page

        with self.login_user_context(self._admin_user):
            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Added Plugin"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_move_plugin(self):
        """
        When a plugin is moved a log entry is created.
        """
        plugin = self._add_plugin()
        endpoint = self.get_move_plugin_uri(plugin)
        page = plugin.placeholder.page
        data = {
            'plugin_id': plugin.pk,
            'target_language': 'en',
            'placeholder_id': self._placeholder_2.pk,
        }

        with self.login_user_context(self._admin_user):
            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Moved Plugin"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_change_plugin(self):
        """
        When a plugin is changed a log entry is created.
        """
        plugin = self._add_plugin()
        endpoint = self.get_admin_url(Page, 'edit_plugin', plugin.pk)
        endpoint += '?cms_path=/en/'
        page = plugin.placeholder.page

        data = {'name': 'A Link 2', 'external_link': 'https://www.django-cms.org'}

        with self.login_user_context(self._admin_user):
            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Changed Plugin"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_delete_plugin(self):
        """
        When a plugin is deleted a log entry is created.
        """
        plugin = self._add_plugin()
        endpoint = self.get_admin_url(Page, 'delete_plugin', plugin.pk)
        endpoint += '?cms_path=/en/'
        page = plugin.placeholder.page

        with self.login_user_context(self._admin_user):
            data = {'post': True}
            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 302)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Deleted Plugin"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_cut_plugin(self):
        """
        When a plugin is cut a log entry is created.
        """
        user_settings = UserSettings.objects.create(
            language="en",
            user=self._admin_user,
            clipboard=Placeholder.objects.create(slot='clipboard'),
        )
        plugin = self._add_plugin()
        endpoint = self.get_move_plugin_uri(plugin)
        page = plugin.placeholder.page
        data = {
            'plugin_id': plugin.pk,
            'target_language': 'en',
            'placeholder_id': user_settings.clipboard_id,
        }

        with self.login_user_context(self._admin_user):
            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Cut Plugin"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_paste_plugin(self):
        """
        When a plugin is pasted a log entry is created.
        """
        user_settings = UserSettings.objects.create(
            language="en",
            user=self._admin_user,
            clipboard=Placeholder.objects.create(slot='clipboard'),
        )
        plugin = self._add_plugin(placeholder=user_settings.clipboard)
        endpoint = self.get_move_plugin_uri(plugin)
        page = self._placeholder_1.page
        data = {
            'plugin_id': plugin.pk,
            'placeholder_id': self._placeholder_1.pk,
            'target_language': 'en',
            'move_a_copy': 'true',
            'plugin_order[]': ['__COPY__'],
        }

        with self.login_user_context(self._admin_user):
            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Paste Plugin"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_add_plugin_to_placeholder(self):
        """
        When a plugin is added to a placeholder a log entry is created.
        """
        plugin = self._add_plugin()
        endpoint = self.get_admin_url(Page, 'copy_plugins') + '?cms_path=/en/'
        page = plugin.placeholder.page

        data = {
            'source_language': 'en',
            'source_placeholder_id': self._placeholder_1.pk,
            'target_language': 'de',
            'target_placeholder_id': self._placeholder_2.pk,
        }

        with self.login_user_context(self._admin_user):
            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Added plugins to placeholder from clipboard"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_paste_placeholder(self):
        """
        When a plugin is pasted in a placeholder a log entry is created.
        """
        user_settings = UserSettings.objects.create(
            language="en",
            user=self._admin_user,
            clipboard=Placeholder.objects.create(slot='clipboard'),
        )
        placeholder_plugin = self._add_plugin(
            user_settings.clipboard,
            'PlaceholderPlugin',
        )
        ref_placeholder = placeholder_plugin.placeholder_ref

        self._add_plugin(ref_placeholder)

        endpoint = self.get_move_plugin_uri(placeholder_plugin)
        page = self._placeholder_1.page

        data = {
            'plugin_id': placeholder_plugin.pk,
            'placeholder_id': self._placeholder_1.pk,
            'target_language': 'en',
            'move_a_copy': 'true',
            'plugin_order[]': ['__COPY__'],
        }

        with self.login_user_context(self._admin_user):
            response = self.client.post(endpoint, data)
            # Test that the end point is valid
            self.assertEqual(response.status_code, 200)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Paste to Placeholder"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)

    def test_log_for_clear_placeholder(self):
        """
        When a placeholder is emptied of plugins a log entry is created.
        """
        self._add_plugin()
        endpoint = self.get_clear_placeholder_url(self._placeholder_1)
        page = self._placeholder_1.page

        with self.login_user_context(self._admin_user):
            response = self.client.post(endpoint, {'test': 0})
            # Test that the end point is valid
            self.assertEqual(response.status_code, 302)
            # Test that the log count is correct
            self.assertEqual(1, LogEntry.objects.count())

            log_entry = LogEntry.objects.all()[0]
            # Check that the contents of the log message is correct
            self.assertEqual(_("Cleared Placeholder"), log_entry.change_message)
            # Check the action flag is set correctly
            self.assertEqual(CHANGE, log_entry.action_flag)
            # Check the object id is set correctly
            self.assertEqual(str(page.pk), log_entry.object_id)
            # Check the object_repr is set correctly
            self.assertEqual(str(page), log_entry.object_repr)
