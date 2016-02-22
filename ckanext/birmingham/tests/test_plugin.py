'''Tests for plugin.py.'''
import collections

import mock
import pylons.config as config
import webtest
import nose.tools

import ckan.plugins.toolkit as toolkit
import ckan.config.middleware
import ckan.new_tests.factories as factories
import ckan.new_tests.helpers as helpers

import ckanext.birmingham.plugin as plugin


def _equal_unordered(list_1, list_2):
    '''Return True if list_1 and list_2 have the same items, False otherwise.

    Unlike == this will return True if the lists contain the same items but in
    a different order.

    '''
    return collections.Counter(list_1) == collections.Counter(list_2)


class TestEditorsAndAdmins(object):

    '''Functional tests for the editors_and_admins() function.'''

    def setup(self):
        helpers.reset_db()

    def test_editors_and_admins_with_0_editors_or_admins(self):
        '''Should return an empty list when there are no editors or admins.'''
        assert plugin.editors_and_admins() == []

    def test_editors_and_admins_with_1_duplicate_admin(self):
        '''Test editors_and_admins() with one user who is admin of two groups.

        Should return a list with just the one user's ID.

        '''
        user = factories.User()
        factories.Organization(user=user)
        factories.Group(user=user)

        assert plugin.editors_and_admins() == [user['id']]

    def test_editors_and_admins_with_1_admin_and_2_editors(self):
        admin = factories.User()
        org = factories.Organization(user=admin)
        editor_1 = factories.User()
        helpers.call_action('organization_member_create',
                            context={'user': admin['name']},
                            id=org['id'], username=editor_1['name'], role='editor')
        editor_2 = factories.User()
        helpers.call_action('organization_member_create',
                            context={'user': admin['name']},
                            id=org['id'], username=editor_2['name'], role='editor')

        assert _equal_unordered(plugin.editors_and_admins(),
                                [admin['id'], editor_1['id'], editor_2['id']])


    def test_editors_and_admins_with_2_editors_and_2_admins(self):
        admin_1 = factories.User()
        org_1 = factories.Organization(user=admin_1)
        admin_2 = factories.User()
        helpers.call_action('organization_member_create',
                            context={'user': admin_1['name']},
                            id=org_1['id'], username=admin_2['name'], role='admin')
        org_2 = factories.Organization(user=admin_1)
        editor = factories.User()
        helpers.call_action('organization_member_create',
                            context={'user': admin_1['name']},
                            id=org_2['id'], username=editor['name'], role='editor')

        assert _equal_unordered(plugin.editors_and_admins(),
                                [admin_1['id'], admin_2['id'], editor['id']])


class TestSysadmins:
    '''Functional tests for the sysadmins function.'''

    def setup(self):
        helpers.reset_db()


    def test_sysadmins_with_0_sysadmins(self):
        assert plugin.sysadmins() == []


    def test_sysadmins_with_1_sysadmin(self):
        sysadmin = factories.Sysadmin()

        assert plugin.sysadmins() == [sysadmin['id']]


    def test_sysadmins_with_3_sysadmins(self):
        sysadmin_1 = factories.Sysadmin()
        sysadmin_2 = factories.Sysadmin()
        sysadmin_3 = factories.Sysadmin()

        assert _equal_unordered(
            plugin.sysadmins(),
            [sysadmin_1['id'], sysadmin_2['id'], sysadmin_3['id']])


def _editor_create_data_dict():
    '''Return a data_dict similar to what would be passed to the
    member_create() action function to create a new editor.

    '''
    return {'id': 'fake_organization_id',
            'object': 'fake_user_id',
            'object_type': 'user',
            'capacity': 'editor'}


class TestMemberCreate:

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_with_no_editors(self, sysadmins, editors_and_admins):
        '''If there are no editors, admins or sysadmins and max_editors > 0
        then member_create should allow creating a new editor.

        '''
        sysadmins.return_value = []
        editors_and_admins.return_value = []

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=3)

        assert result['success'] is True

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_with_1_editor_and_1_admin(self, sysadmins, editors_and_admins):
        '''If there are less than max_editors editors/admins/sysadmins then
        member_create should allow creating a new editor.

        '''
        sysadmins.return_value = ['sysadmin']
        editors_and_admins.return_value = ['editor']

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=3)

        assert result['success'] is True

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_with_2_editors_and_1_sysadmin(self, sysadmins, editors_and_admins):
        '''If the number of editors/admins/sysadmins is equal to max_editors,
        then member_create should not allow a new editor to be created.

        '''
        sysadmins.return_value = ['sysadmin']
        editors_and_admins.return_value = ['editor_1', 'editor_2']

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=3)

        assert result['success'] is False

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_with_2_editors_and_2_sysadmins(self, sysadmins,
                                            editors_and_admins):
        '''If the number of editors/admins/sysadmins is greater than
        max_editors then member_create should not allow a new editor to be
        created.

        '''
        sysadmins.return_value = ['sysadmin_1', 'sysadmin_2']
        editors_and_admins.return_value = ['editor_1', 'editor_2']

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=3)

        assert result['success'] is False

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_with_max_editors_0(self, sysadmins, editors_and_admins):
        '''If max_editors is 0 and there are no editors/admins/sysadmins you
        still shouldn't be allowed to create a new editor.

        '''
        sysadmins.return_value = []
        editors_and_admins.return_value = []

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=0)

        assert result['success'] is False

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_with_4_editors_and_max_editors_5(self, sysadmins,
                                              editors_and_admins):
        '''If max_editors is 5 and there are less than 5
        editors/admins/sysadmins then you should be able to create a new
        editor.

        '''
        sysadmins.return_value = ['sysadmin_1', 'sysadmin_2']
        editors_and_admins.return_value = ['editor', 'admin']

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=5)

        assert result['success'] is True

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_with_5_editors_and_max_editors_5(self, sysadmins,
                                              editors_and_admins):
        '''If max_editors is 5 and there are 5 editors/admins/sysadmins
        then you shouldn't be able to create another editor.

        '''
        sysadmins.return_value = ['sysadmin_1', 'sysadmin_2', 'sysadmin_3']
        editors_and_admins.return_value = ['editor', 'admin']

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=5)

        assert result['success'] is False

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_with_6_editors_and_max_editors_5(self, sysadmins,
                                              editors_and_admins):
        '''If max_editors is 5 and there are more than 5
        editors/admins/sysadmins then you shouldn't be able to create another
        editor.

        '''
        sysadmins.return_value = ['sysadmin_1', 'sysadmin_2', 'sysadmin_3']
        editors_and_admins.return_value = ['editor', 'admin', 'editor_2']

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=5)

        assert result['success'] is False

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_does_not_double_count(self, sysadmins, editors_and_admins):
        '''If the same user is both an editor/admin and a sysadmin, they
        should not be counted twice towards max_editors.

        '''
        sysadmins.return_value = ['user_1', 'user_2']
        editors_and_admins.return_value = ['user_1']

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=3)

        assert result['success'] is True

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_does_count_duplicates_once(self, sysadmins, editors_and_admins):
        '''If the same user is both an editor/admin and a sysadmin, they
        *should* be counted once towards max_editors.

        '''
        sysadmins.return_value = ['user_1', 'user_2', 'user_3']
        editors_and_admins.return_value = ['user_1']

        result = plugin._member_create(_editor_create_data_dict(),
                                       {'success': True}, max_editors=3)

        assert result['success'] is False

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_returns_False_when_core_returns_False(self, sysadmins,
                                                   editors_and_admins):
        '''If the result from the core member_create auth function has
        'success': False then the custom auth function should return that
        result, even if it would otherwise have returned 'success': True.

        '''
        sysadmins.return_value = ['user_1']
        editors_and_admins.return_value = ['user_1']
        core_result = {'success': False, 'msg': 'CKAN core says no'}
        result = plugin._member_create(_editor_create_data_dict(),
                                       core_result, max_editors=3)

        assert result == core_result

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_can_still_create_members(self, sysadmins, editors_and_admins):
        '''It should still be possible to create (non-editor) group/org
        members, even when the number of editors/admins/sysadmins is equal to
        max_editors.

        '''
        sysadmins.return_value = ['user_1', 'user_2']
        editors_and_admins.return_value = ['user_3']

        # A data_dict similar to what would be passed to the member_create
        # action function to create a normal (non-editor) member.
        data_dict = {'id': 'fake_organization_id',
                     'object': 'fake_user_id',
                     'object_type': 'user',
                     'capacity': 'member'}

        result = plugin._member_create(data_dict, {'success': True},
                                       max_editors=3)

        assert result['success'] is True

    @mock.patch('ckanext.birmingham.plugin.editors_and_admins')
    @mock.patch('ckanext.birmingham.plugin.sysadmins')
    def test_cannot_create_too_many_admins(self, sysadmins,
                                           editors_and_admins):
        '''If there are already max_editors editors/admins/sysadmins, it should
        not be possible to create another group/org admin.

        All the tests above tested creating group/org editors, this is just
        one test that creating admins is also blocked.

        '''
        sysadmins.return_value = ['user_1', 'user_2']
        editors_and_admins.return_value = ['user_3']

        # A data_dict similar to what would be passed to the member_create
        # action function to create a group or organization admin.
        data_dict = {'id': 'fake_organization_id',
                     'object': 'fake_user_id',
                     'object_type': 'user',
                     'capacity': 'admin'}

        result = plugin._member_create(data_dict, {'success': True},
                                       max_editors=3)

        assert result['success'] is False


def _load_plugin(plugin_name):
    '''Add the given plugin to the ckan.plugins config setting.

    :param plugin: the plugin to add, e.g. ``datastore``
    :type plugin: string

    '''
    plugins = set(config['ckan.plugins'].strip().split())
    plugins.add(plugin_name.strip())
    config['ckan.plugins'] = ' '.join(plugins)


def _get_test_app():
    '''Return a webtest.TestApp for CKAN, with legacy templates disabled.'''
    config['ckan.legacy_templates'] = False
    app = ckan.config.middleware.make_app(config['global_conf'], **config)
    app = webtest.TestApp(app)
    return app


class TestUpToNEditorsPlugin(object):

    ''''Functional/integration tests for class UpToNEditorsPlugin.'''

    @classmethod
    def setup_class(cls):
        # Make a copy of the Pylons config, so we can restore it in teardown.
        cls.original_config = config.copy()
        _load_plugin('up_to_n_editors')
        cls.app = _get_test_app()

    def setup(self):
        import ckan.model as model
        model.Session.close_all()
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        # Restore the Pylons config to its original values, in case any tests
        # changed any config settings.
        config.clear()
        config.update(cls.original_config)

    def test_organization_member_create_successful(self):
        '''Test creating a new editor when it should succeed.'''
        organization_admin = factories.User()
        organization = factories.Organization(user=organization_admin)
        editor = factories.User()

        url = toolkit.url_for(controller='api',
                              logic_function='organization_member_create',
                              action='action', ver=3)
        data_dict = {'id': organization['id'], 'username': editor['name'],
                     'role': 'editor'}
        response = self.app.post_json(
            url, data_dict,
            extra_environ={'REMOTE_USER': str(organization_admin['name'])})

        members = helpers.call_action('member_list', id=organization['id'])
        assert (editor['id'], 'user', 'Editor') in members

    def test_organizaiton_member_create_unsuccessful(self):
        '''Test creating a new editor when it should not succeed.'''
        organization_admin = factories.User()
        organization = factories.Organization(user=organization_admin)
        editor_1 = factories.User()
        helpers.call_action('organization_member_create',
                            context={'user': organization_admin['name']},
                            id=organization['id'], username=editor_1['name'],
                            role='editor')
        editor_2 = factories.User()
        helpers.call_action('organization_member_create',
                            context={'user': organization_admin['name']},
                            id=organization['id'], username=editor_2['name'],
                            role='editor')

        # We should not be able to create another editor.
        editor_3 = factories.User()
        url = toolkit.url_for(controller='api',
                              logic_function='organization_member_create',
                              action='action', ver=3)
        data_dict = {'id': organization['id'], 'username': editor_3['name'],
                     'role': 'editor'}
        response = self.app.post_json(
            url, data_dict,
            extra_environ={'REMOTE_USER': str(organization_admin['name'])},
            status=403)

        # Test that we were denied for the right reason.
        # (This catches mistakes in the tests, for example if the test didn't
        # pass REMOTE_USER we would get a 403 but for a different reason.)
        assert response.json['error']['message'] == ("Access denied: You're "
                                                     "only allowed to have 3 "
                                                     "editors")

    def test_organization_member_create_with_max_editors_5(self):
        '''Test that setting max_editors to 5 in the config file works.

        If we edit the config, we should be allowed to create one admin and
        4 editors, but no more.

        '''
        config['ckan.birmingham.max_editors'] = '5'
        organization_admin = factories.User()
        organization = factories.Organization(user=organization_admin)
        editor_1 = factories.User()
        editor_2 = factories.User()
        editor_3 = factories.User()
        editor_4 = factories.User()

        # This should not fail - we should be allowed to have one admin and
        # three editors.
        for editor in (editor_1, editor_2, editor_3):
            helpers.call_action(
                'organization_member_create',
                context={'user': organization_admin['name']},
                id=organization['id'], username=editor['name'], role='editor')

        # At this point we have 4 "editors" (one admin and three editors)
        # and max_editors is 5, so we should be allowed to add one more editor.
        url = toolkit.url_for(controller='api',
                              logic_function='organization_member_create',
                              action='action', ver=3)
        data_dict = {'id': organization['id'], 'username': editor_4['name'],
                     'role': 'editor'}
        response = self.app.post_json(
            url, data_dict,
            extra_environ={'REMOTE_USER': str(organization_admin['name'])})

        members = helpers.call_action('member_list', id=organization['id'])
        assert (organization_admin['id'], 'user', 'Admin') in members
        for editor in (editor_1, editor_2, editor_3, editor_4):
            assert (editor['id'], 'user', 'Editor') in members

        # At this point we should not be allowed to create any more editors
        # though.
        editor_5 = factories.User()
        url = toolkit.url_for(controller='api',
                              logic_function='organization_member_create',
                              action='action', ver=3)
        data_dict = {'id': organization['id'], 'username': editor_5['name'],
                     'role': 'editor'}
        response = self.app.post_json(url, data_dict,
            extra_environ={'REMOTE_USER': str(organization_admin['name'])},
            status=403)

        # Test that we were denied for the right reason.
        # (This catches mistakes in the tests, for example if the test didn't
        # pass REMOTE_USER we would get a 403 but for a different reason.)
        assert response.json['error']['message'] == ("Access denied: You're "
                                                     "only allowed to have 5 "
                                                     "editors")

    def test_group_member_create(self):
        '''Test that the group_member_create API is also blocked.'''
        group_admin = factories.User()
        group = factories.Group(user=group_admin)
        editor_1 = factories.User()
        helpers.call_action('group_member_create',
                            context={'user': group_admin['name']},
                            id=group['id'], username=editor_1['name'],
                            role='editor')
        editor_2 = factories.User()
        helpers.call_action('group_member_create',
                            context={'user': group_admin['name']},
                            id=group['id'], username=editor_2['name'],
                            role='editor')

        editor_3 = factories.User()
        nose.tools.assert_raises(toolkit.NotAuthorized, helpers.call_action,
                                 'group_member_create',
                                 context={'user': group_admin['name']},
                                 id=group['id'],
                                 username=editor_3['name'], role='editor')
        url = toolkit.url_for(controller='api',
                              logic_function='group_member_create',
                              action='action', ver=3)
        data_dict = {'id': group['id'], 'username': editor_3['id'],
                     'role': 'editor'}
        response = self.app.post_json(url, data_dict,
            extra_environ={'REMOTE_USER': str(group_admin['name'])},
            status=403)

        # Test that we were denied for the right reason.
        # (This catches mistakes in the tests, for example if the test didn't
        # pass REMOTE_USER we would get a 403 but for a different reason.)
        assert response.json['error']['message'] == ("Access denied: You're "
                                                     "only allowed to have 3 "
                                                     "editors")

    def test_member_create(self):
        '''Test that the member_create API is also blocked.

        Most of the tests above use organization_member_create.

        '''
        organization_admin = factories.User()
        organization = factories.Organization(user=organization_admin)
        editor_1 = factories.User()
        helpers.call_action('member_create',
                            context={'user': organization_admin['name']},
                            id=organization['id'], object=editor_1['id'],
                            object_type='user', capacity='editor')
        editor_2 = factories.User()
        helpers.call_action('member_create',
                            context={'user': organization_admin['name']},
                            id=organization['id'], object=editor_2['id'],
                            object_type='user', capacity='editor')

        # We should not be able to create another editor.
        editor_3 = factories.User()
        url = toolkit.url_for(controller='api', logic_function='member_create',
                              action='action', ver=3)
        data_dict = {'id': organization['id'], 'object': editor_3['id'],
                     'object_type': 'user', 'capacity': 'editor'}
        response = self.app.post_json(url, data_dict,
            extra_environ={'REMOTE_USER': str(organization_admin['name'])},
            status=403)

        # Test that we were denied for the right reason.
        # (This catches mistakes in the tests, for example if the test didn't
        # pass REMOTE_USER we would get a 403 but for a different reason.)
        assert response.json['error']['message'] == ("Access denied: You're "
                                                     "only allowed to have 3 "
                                                     "editors")
