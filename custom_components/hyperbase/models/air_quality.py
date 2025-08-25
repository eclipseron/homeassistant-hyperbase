class AirQColumns:
    def __init__(self):
        self.__columns = {
            "airq_particulate_matter_2_5": {"kind": "double", "required": False},
            "airq_particulate_matter_10": {"kind": "double", "required": False},
            "airq_particulate_matter_0_1": {"kind": "double", "required": False},
            "airq_air_quality_index": {"kind": "double", "required": False},
            "airq_ozone": {"kind": "double", "required": False},
            "airq_carbon_monoxide": {"kind": "double", "required": False},
            "airq_carbon_dioxide": {"kind": "double", "required": False},
            "airq_sulphur_dioxide": {"kind": "double", "required": False},
            "airq_nitrogen_oxide": {"kind": "double", "required": False},
            "airq_nitrogen_monoxide": {"kind": "double", "required": False},
            "airq_nitrogen_dioxide": {"kind": "double", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class AirQEntityData:
    def __init__(self,
        particulate_matter_2_5: float | None = None,
        particulate_matter_10: float | None = None,
        particulate_matter_0_1: float | None = None,
        air_quality_index: float | None = None,
        ozone: float | None = None,
        carbon_monoxide: float | None = None,
        carbon_dioxide: float | None = None,
        sulphur_dioxide: float | None = None,
        nitrogen_oxide: float | None = None,
        nitrogen_monoxide: float | None = None,
        nitrogen_dioxide: float | None = None,
        ):
        self._particulate_matter_2_5 = particulate_matter_2_5
        self._particulate_matter_10 = particulate_matter_10
        self._particulate_matter_0_1 = particulate_matter_0_1
        self._air_quality_index = air_quality_index
        self._ozone = ozone
        self._carbon_monoxide = carbon_monoxide
        self._carbon_dioxide = carbon_dioxide
        self._sulphur_dioxide = sulphur_dioxide
        self._nitrogen_oxide = nitrogen_oxide
        self._nitrogen_monoxide = nitrogen_monoxide
        self._nitrogen_dioxide = nitrogen_dioxide
    
    @property
    def data(self):
        return {
            "airq_particulate_matter_2_5": self._particulate_matter_2_5,
            "airq_particulate_matter_10": self._particulate_matter_10,
            "airq_particulate_matter_0_1": self._particulate_matter_0_1,
            "airq_air_quality_index": self._air_quality_index,
            "airq_ozone": self._ozone,
            "airq_carbon_monoxide": self._carbon_monoxide,
            "airq_carbon_dioxide": self._carbon_dioxide,
            "airq_sulphur_dioxide": self._sulphur_dioxide,
            "airq_nitrogen_oxide": self._nitrogen_oxide,
            "airq_nitrogen_monoxide": self._nitrogen_monoxide,
            "airq_nitrogen_dioxide": self._nitrogen_dioxide,
        }