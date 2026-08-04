class ReviveService:
    def __init__(
        self,
        ebay_access_token: str | None = None,
        google_api_key: str | None = None,
    ):
        self.ebay_access_token = ebay_access_token or os.getenv("EBAY_ACCESS_TOKEN")
        self.repair_places = RepairPlacesService(api_key=google_api_key)