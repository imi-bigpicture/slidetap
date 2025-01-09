import { Attribute } from "models/attribute"
import { ValueDisplayType } from "models/value_display_type"

export function selectValueToDisplay<valueType>(
    attribute: Attribute<valueType>,
    valueToDisplay: ValueDisplayType
): valueType | undefined {
    if (valueToDisplay === ValueDisplayType.CURRENT) {
      if (attribute.updatedValue !== undefined && attribute.updatedValue !== null ) {
        return attribute.updatedValue
      }
      if (attribute.mappedValue !== undefined && attribute.mappableValue !== null) {
        return attribute.mappedValue
      }
      return attribute.originalValue
    }
    if (valueToDisplay === ValueDisplayType.ORIGINAL) {
      return attribute.originalValue
    }
    if (valueToDisplay === ValueDisplayType.UPDATED) {
      return attribute.updatedValue
    }
    if (valueToDisplay === ValueDisplayType.MAPPED) {
      return attribute.mappedValue
    }
  }