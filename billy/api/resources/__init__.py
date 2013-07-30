# Generic
from base import Base

#Fluff
from api.resources.base import Home

#API RESOURCES
from api.resources.group import GroupController
from api.resources.customer import (CustomerIndexController,
                                    CustomerController, customer_view,
                                    CustomerCreateForm, CustomerUpdateForm)
from api.resources.coupon import (CouponIndexController, CouponController,
                                  coupon_view, CouponCreateForm,
                                    CouponUpdateForm)
from api.resources.plan import (PlanIndexController, PlanController, plan_view, PlanCreateForm, PlanUpdateForm)
from api.resources.payout import (PayoutIndexController, PayoutController,
                                  payout_view, PayoutCreateForm, PayoutUpdateForm)
from api.resources.plan_subscription import (PlanSubIndexController,
                                             PlanSubController, plan_sub_view, PlanSubCreateForm, PlanSubDeleteForm)
from api.resources.payout_subscription import (PayoutSubIndexController,
                                               PayoutSubController,
                                               payout_sub_view, PayoutSubCreateForm, PayoutSubDeleteForm)
from api.resources.plan_invoice import (PlanInvController,
                                        PlanInvIndexController, plan_inv_view)
from api.resources.payout_invoice import (PayoutInvController,
                                          PayoutInvIndexController,
                                          payout_inv_view)
from api.resources.plan_transaction import (PlanTransIndexController,
                                            PlanTransController,
                                            plan_trans_view)
from api.resources.payout_transaction import (PayoutTransIndexController,
                                              PayoutTransController,
                                              payout_trans_view)
