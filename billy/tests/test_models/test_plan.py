import datetime

from billy.tests.helper import ModelTestCase


class TestPlanModel(ModelTestCase):

    def make_one(self, *args, **kwargs):
        from billy.models.plan import PlanModel
        return PlanModel(*args, **kwargs)

    def test_create_plan(self):
        model = self.make_one(self.session)
        name = 'monthly billing to user John'
        amount = 5566.77
        frequency = model.FREQ_MONTHLY
        guid = model.create_plan(
            name=name,
            amount=amount,
            frequency=frequency,
        )
        plan = model.get_plan_by_guid(guid)
        self.assertEqual(plan.guid, guid)
        self.assertEqual(plan.name, name)
        self.assertEqual(plan.amount, amount)
        self.assertEqual(plan.frequency, frequency)
        self.assertEqual(plan.active, True)
        self.assertEqual(plan.created_at, self.now)
        self.assertEqual(plan.updated_at, self.now)

    def test_create_plan_with_wrong_frequency(self):
        model = self.make_one(self.session)

        with self.assertRaises(ValueError):
            model.create_plan(
                name=None,
                amount=999,
                frequency=999,
            )

    def test_get_plan(self):
        import transaction
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create_plan(
                name='evil gangster charges protection fee from Tom weekly',
                amount=99.99,
                frequency=model.FREQ_WEEKLY,
            )

        plan = model.get_plan_by_guid('not-exist')
        self.assertEqual(plan, None)

        plan = model.get_plan_by_guid(guid)
        self.assertNotEqual(plan, None)

    def test_update_plan(self):
        import transaction
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create_plan(
                name='evil gangster charges protection fee from Tom weekly',
                amount=99.99,
                frequency=model.FREQ_WEEKLY,
            )

        # advanced the current date time
        self.now += datetime.timedelta(seconds=10)
        name = 'new plan name'
        active = False

        with transaction.manager:
            model.update_plan(
                guid=guid,
                name=name,
                active=active,
            )

        plan = model.get_plan_by_guid(guid)
        self.assertEqual(plan.name, name)
        self.assertEqual(plan.active, active)
        self.assertEqual(plan.updated_at, self.now)

        # advanced the current date time
        self.now += datetime.timedelta(seconds=10)

        # this should update the updated_at field only
        with transaction.manager:
            model.update_plan(guid)

        plan = model.get_plan_by_guid(guid)
        self.assertEqual(plan.name, name)
        self.assertEqual(plan.active, active)
        self.assertEqual(plan.updated_at, self.now)

        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            model.update_plan(guid, wrong_arg=True, neme='john')