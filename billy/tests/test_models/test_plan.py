from billy.tests.helper import ModelTestCase


class TestPlanModel(ModelTestCase):

    def make_one(self, *args, **kwargs):
        from billy.models.plan import PlanModel
        return PlanModel(*args, **kwargs)

    def test_create_plan(self):
        model = self.make_one(self.session)
        name = 'monthly billing to user john'
        amount = 5566.77
        frequency = model.FREQ_MONTHLY
        guid = model.create_plan(
            name=name,
            amount=amount,
            frequency=model.FREQ_MONTHLY,
        )
        plan = model.get_plan_by_guid(guid)
        self.assertEqual(plan.guid, guid)
        self.assertEqual(plan.name, name)
        self.assertEqual(plan.amount, amount)
        self.assertEqual(plan.frequency, frequency)
        self.assertEqual(plan.created_at, self.now)
        self.assertEqual(plan.updated_at, self.now)
