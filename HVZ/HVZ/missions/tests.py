from datetime import timedelta

from django.core.urlresolvers import reverse
from django.test.client import Client
from django.conf import settings

from HVZ.basetest import BaseTest, HUGH_MANN, ROB_ZOMBIE
from HVZ.main.models import Player, Game
from HVZ.missions.models import Mission, Plot

MISSION = Mission(
    day=settings.NOW().date(),
    time="N",
)

ZOMBIE_PLOT = Plot(
    title="Tonight, we dine in Hell!",
    slug="tonight-we-dine-in-hell",

    team='Z',

    before_story="Nommin' in Nam.",
    before_story_markup_type="markdown",

    victory_story="Zombies done won.",
    victory_story_markup_type="markdown",

    defeat_story="Zombies done lost.",
    defeat_story_markup_type="markdown",

    visible=True,
)

HUMAN_PLOT = Plot(
    title="Friends, Romans, Countrymen.",
    slug="friends-romans-countrymen",

    team='H',

    before_story="Lend me your ears",
    before_story_markup_type="markdown",

    victory_story="Humans done won.",
    victory_story_markup_type="markdown",

    defeat_story="Humans done lost.",
    defeat_story_markup_type="markdown",

    visible=True,
)

class SingleMissionTest(BaseTest):

    def setUp(self):
        """Create the players who will view the missions."""
        c = Client()
        self.login_as_tabler(c)

        c.post(reverse('register'), ROB_ZOMBIE)
        z = Player.objects.get()
        z.team = 'Z'
        z.save()

        c.post(reverse('register'), HUGH_MANN)

        # Create the mission and its plot views
        MISSION.game = Game.objects.get()
        MISSION.full_clean()
        MISSION.save()

        m = Mission.objects.get()

        HUMAN_PLOT.mission = m
        HUMAN_PLOT.full_clean()
        HUMAN_PLOT.save()

        ZOMBIE_PLOT.mission = m
        ZOMBIE_PLOT.full_clean()
        ZOMBIE_PLOT.save()

    def tearDown(self):
        Mission.objects.all().delete()
        Plot.objects.all().delete()

    def test_logged_out(self):
        c = Client()
        uri = reverse('plot_detail', args=(HUMAN_PLOT.id, HUMAN_PLOT.slug))
        r = c.get(uri)
        self.assertRedirects(r, '/login/?next=%s' % uri)

    def test_invalid_url(self):
        c = Client()
        c.post(reverse('login'), HUGH_MANN)
        r = c.get(reverse('plot_detail', args=(42, 'totes-invalid')))

        self.assertEqual(r.status_code, 404)

    def test_list_perspectives(self):
        """Check that each team sees a different list of missions."""
        c = Client()

        # Human
        c.post(reverse('login'), HUGH_MANN)
        response = c.get(reverse('plot_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['plot_list'][0], HUMAN_PLOT)

        # Zombie
        response = c.post(reverse('login'), ROB_ZOMBIE)
        response = c.get(reverse('plot_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['plot_list'][0], ZOMBIE_PLOT)

    def test_access_restrictions(self):
        """Ensure that humans can't access zombie plots, and vice versa."""
        c = Client()

        # Human
        c.post(reverse('login'), HUGH_MANN)

        response = c.get(reverse('plot_detail',
                                 args=(HUMAN_PLOT.id, HUMAN_PLOT.slug)))
        self.assertEqual(response.status_code, 200)

        response = c.get(reverse('plot_detail',
                                 args=(ZOMBIE_PLOT.id, ZOMBIE_PLOT.slug)))
        self.assertEqual(response.status_code, 403)

        # Zombie
        c.post(reverse('login'), ROB_ZOMBIE)

        response = c.get(reverse('plot_detail',
                                 args=(ZOMBIE_PLOT.id, ZOMBIE_PLOT.slug)))
        self.assertEqual(response.status_code, 200)

        response = c.get(reverse('plot_detail',
                                 args=(HUMAN_PLOT.id, HUMAN_PLOT.slug)))
        self.assertEqual(response.status_code, 403)

    def test_visibility_override(self):
        """A false visibility should prevent us from seeing a mission."""
        c = Client()

        human_plot = Plot.objects.get(team='H')
        human_plot.visible = False
        human_plot.reveal_time = settings.NOW() - timedelta(hours=1)
        human_plot.save()

        # We should not see any missions.
        c.post(reverse('login'), HUGH_MANN)
        response = c.get(reverse('plot_list'))
        self.assertFalse(response.context_data['plot_list'])

    def test_visibility_restriction(self):
        """We should be able to see a mission with a reveal time in the past."""
        c = Client()

        # Set a revealed mission
        human_plot = Plot.objects.get(team='H')
        human_plot.visible = None
        human_plot.reveal_time = settings.NOW() - timedelta(hours=1)
        human_plot.save()

        # Check for visibility
        c.post(reverse('login'), HUGH_MANN)
        response = c.get(reverse('plot_list'))
        self.assertTrue(response.context_data['plot_list'])

    def test_future_reveal_times(self):
        """We shouldn't see a mission if its reveal time is in the future."""
        c = Client()

        # Set a revealed mission
        human_plot = Plot.objects.get(team='H')
        human_plot.visible = None
        human_plot.reveal_time = settings.NOW() + timedelta(hours=1)
        human_plot.save()

        # Check for visibility
        c.post(reverse('login'), HUGH_MANN)
        response = c.get(reverse('plot_list'))
        self.assertFalse(response.context_data['plot_list'])
