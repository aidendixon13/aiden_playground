# """
# ==============================================================================
# Name: models
# Author:
# Date: 10/13/2025
# Description: Pydantic models for data analysis operations.
# ==============================================================================
# """

# from enum import Enum
# from typing import List, Optional, Union, Any

# from pydantic import BaseModel, Field


# # Enums for Analysis
# class AnalysisType(str, Enum):
#     """Enum for analysis types."""

#     CALC = "Calc"
#     SORT = "Sort"
#     FILTER = "Filter"


# class TargetType(str, Enum):
#     """Enum for target types."""

#     CALC = "Calc"
#     MEMBERS = "Members"


# class SortOrder(str, Enum):
#     """Enum for sort order."""

#     ASCENDING = "Ascending"
#     DESCENDING = "Descending"


# class RowCol(str, Enum):
#     """Enum for row/column specification."""

#     ROW = "Row"
#     COLUMN = "Column"


# class NullHandling(str, Enum):
#     """Enum for null handling."""

#     FIRST = "First"
#     LAST = "Last"
#     EXCLUDE = "Exclude"


# class CalcType(str, Enum):
#     """Enum for calculation types."""

#     VARIANCE = "Variance"
#     PERCENT_OF_TOTAL = "PercentOfTotal"
#     CUMULATIVE = "Cumulative"
#     AVERAGE = "Average"
#     CUSTOM = "Custom"


# class VarianceType(str, Enum):
#     """Enum for variance types."""

#     ABSOLUTE = "Absolute"
#     PERCENT = "Percent"


# class FilterType(str, Enum):
#     """Enum for filter types."""

#     TOP = "TOP"
#     BOTTOM = "BOTTOM"
#     GREATER_THAN = "GREATER_THAN"
#     LESS_THAN = "LESS_THAN"
#     EQUALS = "EQUALS"
#     NOT_EQUALS = "NOT_EQUALS"
#     BETWEEN = "BETWEEN"
#     CONTAINS = "CONTAINS"
#     STARTS_WITH = "STARTS_WITH"
#     ENDS_WITH = "ENDS_WITH"
#     KEEP = "KEEP"
#     REMOVE = "REMOVE"


# class FilterOperator(str, Enum):
#     """Enum for filter operators."""

#     AND = "AND"
#     OR = "OR"


# # Base Models
# class DimensionMember(BaseModel):
#     """
#     Represents a dimension member.

#     Attributes:
#         dim_type (str): The dimension type.
#         member_name (str): The dimension member name.
#         expansion (str): The expansion string.
#         level (int): The hierarchy level.
#     """

#     dim_type: str = Field(alias="DimType")
#     member_name: str = Field(alias="MemberName")
#     expansion: str = Field(alias="Expansion")
#     level: int = Field(alias="Level")

#     class Config:
#         populate_by_name = True


# class TargetSpec(BaseModel):
#     """
#     Base class for target specifications.

#     Attributes:
#         type (TargetType): The target type.
#     """

#     type: TargetType = Field(alias="Type")

#     class Config:
#         populate_by_name = True


# class CalculationSpec(TargetSpec):
#     """
#     Specification for calculations.

#     Attributes:
#         calc_type (CalcType): The calculation type.
#     """

#     calc_type: CalcType = Field(alias="CalcType")


# class VarianceCalc(CalculationSpec):
#     """
#     Variance calculation specification.

#     Attributes:
#         variance_type (VarianceType): The variance type.
#         val1 (DimensionMember): First value for variance calculation.
#         val2 (DimensionMember): Second value for variance calculation.
#     """

#     variance_type: VarianceType = Field(alias="VarianceType")
#     val1: DimensionMember = Field(alias="Val1")
#     val2: DimensionMember = Field(alias="Val2")


# class MemberSpec(TargetSpec):
#     """
#     Specification for members.

#     Attributes:
#         members (List[DimensionMember]): List of dimension members.
#     """

#     members: List[DimensionMember] = Field(alias="Members")


# # Analysis Objects
# class BaseAnalysisObject(BaseModel):
#     """
#     Base class for analysis objects.

#     Attributes:
#         id (str): Unique identifier.
#         name (str): Name of the analysis.
#         analysis_type (AnalysisType): Type of analysis.
#         description (str): Description of the analysis.
#         target (Union[MemberSpec, CalculationSpec, TargetSpec]): Target specification.
#     """

#     analysis_type: AnalysisType = Field(alias="AnalysisType")
#     target: Union[MemberSpec, CalculationSpec, TargetSpec] = Field(alias="Target")

#     class Config:
#         populate_by_name = True


# class BaseSort(BaseAnalysisObject):
#     """
#     Sort analysis object.

#     Attributes:
#         order (SortOrder): Sort order.
#         sort_by (RowCol): Whether to sort by row or column.
#         null_handle (NullHandling): How to handle null values.
#     """

#     order: SortOrder = Field(alias="Order")
#     null_handle: NullHandling = Field(alias="NullHandle")


# class BaseFilter(BaseAnalysisObject):
#     """
#     Filter analysis object.

#     Attributes:
#         condition (str): Filter condition (legacy, human-readable description).
#         filter_type (FilterType): The type of filter operation.
#         value (Optional[float]): Numeric value for comparisons (e.g., for Top 5, value = 5).
#         value2 (Optional[float]): Second value for BETWEEN filters.
#         comparison_member (Optional[DimensionMember]): Dimension member to compare against.
#         filter_operator (FilterOperator): Operator for combining multiple conditions (AND/OR).
#         include (bool): Whether to include or exclude matching items.
#         apply_to_descendants (bool): Whether to apply filter to descendants.
#     """

#     filter_type: Optional[FilterType] = Field(default=None, alias="FilterType")
#     value: Optional[float] = Field(default=None, alias="Value")
#     value2: Optional[float] = Field(default=None, alias="Value2")
#     comparison_member: Optional[DimensionMember] = Field(default=None, alias="ComparisonMember")
#     filter_operator: Optional[FilterOperator] = Field(default=None, alias="FilterOperator")
#     include: bool = Field(alias="Include")
#     apply_to_descendants: bool = Field(alias="ApplyToDescendants")


# # POV Model
# class POV(BaseModel):
#     """
#     Point of View model representing dimension context.

#     Attributes:
#         cube_name (str): Name of the cube.
#         entity (str): Entity dimension.
#         parent (str): Parent dimension.
#         consolidation (str): Consolidation dimension.
#         scenario (str): Scenario dimension.
#         time (str): Time dimension.
#         view (str): View dimension.
#         account (str): Account dimension.
#         flow (str): Flow dimension.
#         origin (str): Origin dimension.
#         ic (str): IC dimension.
#         ud1 (str): User dimension 1.
#         ud2 (str): User dimension 2.
#         ud3 (str): User dimension 3.
#         ud4 (str): User dimension 4.
#         ud5 (str): User dimension 5.
#         ud6 (str): User dimension 6.
#         ud7 (str): User dimension 7.
#         ud8 (str): User dimension 8.
#     """

#     cube_name: str = Field(alias="CubeName")
#     entity: str = Field(alias="Entity")
#     parent: str = Field(alias="Parent")
#     consolidation: str = Field(alias="Consolidation")
#     scenario: str = Field(alias="Scenario")
#     time: str = Field(alias="Time")
#     view: str = Field(alias="View")
#     account: str = Field(alias="Account")
#     flow: str = Field(alias="Flow")
#     origin: str = Field(alias="Origin")
#     ic: str = Field(alias="IC")
#     ud1: str = Field(alias="UD1")
#     ud2: str = Field(alias="UD2")
#     ud3: str = Field(alias="UD3")
#     ud4: str = Field(alias="UD4")
#     ud5: str = Field(alias="UD5")
#     ud6: str = Field(alias="UD6")
#     ud7: str = Field(alias="UD7")
#     ud8: str = Field(alias="UD8")

#     class Config:
#         populate_by_name = True


# # Request/Response Models
# class RequestDimensionMember(BaseModel):
#     """
#     Request model for dimension member.

#     Attributes:
#         dim_type (str): Dimension type.
#         dim_name (str): Dimension name.
#         expansion (str): Expansion string.
#     """

#     dim_type: str = Field(alias="DimType")
#     dim_name: str = Field(alias="DimName")
#     expansion: str = Field(alias="Expansion")

#     class Config:
#         populate_by_name = True


# class ResponseDimensionMember(BaseModel):
#     """
#     Response model for dimension member.

#     Attributes:
#         dim_type (str): Dimension type.
#         dim_name (str): Dimension name.
#         expansion (str): Expansion string.
#         parent_name (str): Parent member name.
#     """

#     dim_type: str = Field(alias="DimType")
#     dim_name: str = Field(alias="DimName")
#     expansion: str = Field(alias="Expansion")
#     parent_name: str = Field(alias="ParentName")

#     class Config:
#         populate_by_name = True


# class Analysis(BaseModel):
#     """
#     Model representing an analysis operation.

#     Attributes:
#         pov (POV): Point of view context.
#         members (List[DimensionMember]): List of dimension members to operate on.
#         analysis_steps (List[BaseAnalysisObject]): List of analysis steps to perform.
#     """

#     row_col: List[DimensionMember] = Field(alias="AnalysisRowCol")
#     analysis_steps: List[Any] = Field(alias="AnalysisSteps")


# class AnalysisRequest(BaseModel):
#     """
#     Request model for analysis operations.

#     Attributes:
#         pov (POV): Point of view context.
#         members (List[DimensionMember]): List of dimension members to operate on.
#         analysis_steps (List[BaseAnalysisObject]): List of analysis steps to perform.
#     """

#     pov: POV = Field(alias="Pov")
#     analysis: List[Analysis] = Field(alias="Analysis")

#     class Config:
#         populate_by_name = True


# class AnalysisResponse(BaseModel):
#     """
#     Response model for analysis operations.

#     Attributes:
#         results (List[ResponseDimensionMember]): List of result dimension members.
#         message (str): Response message.
#         processed_steps (int): Number of steps processed.
#     """

#     results: List[ResponseDimensionMember] = Field(alias="Results")
#     message: str = Field(alias="Message")
#     processed_steps: int = Field(alias="ProcessedSteps")

#     class Config:
#         populate_by_name = True
