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
        model = self.make_one(self.session)
        name = 'evil gangster charges protection fee from Tom weekly'
        amount = 99.99
        frequency = model.FREQ_WEEKLY
        guid = model.create_plan(
            name=name,
            amount=amount,
            frequency=frequency,
        )

        plan = model.get_plan_by_guid('not-exist')
        self.assertEqual(plan, None)

        plan = model.get_plan_by_guid(guid)
        self.assertNotEqual(plan, None)