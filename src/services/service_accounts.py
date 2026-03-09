from lib.util import dict_to_camel_case


class ServiceAccountService:
    @staticmethod
    async def transform_response(service_account):
        data = service_account.to_dict()
        return dict_to_camel_case(data)