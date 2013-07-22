from billy.api.views import Base


class Home(Base):

    def get(self):
        return {
            "Welcome to billy":
            "Checkout here {}".format(
            'https://www.github.com/balanced/billy')
        }
