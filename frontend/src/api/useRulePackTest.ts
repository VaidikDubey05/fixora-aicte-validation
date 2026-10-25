import { useMutation } from '@tanstack/react-query';
import api from '../lib/api';

export interface RulePackTestParams {
  id: string;
  version?: string;
  sampleContext?: Record<string, any>;
  yamlContent?: string;
  case_context?: Record<string, any>;
  rules_yaml?: string;
}

export interface RulePackTestResponse {
  pack_id: string;
  items_evaluated: number;
  results: Record<string, any>[];
}

export function useRulePackTest() {
  return useMutation({
    mutationFn: async ({
      id,
      version,
      sampleContext,
      yamlContent,
      case_context,
      rules_yaml,
    }: RulePackTestParams): Promise<RulePackTestResponse> => {
      const res = await api.post<RulePackTestResponse>(`/rule-packs/${id}/test`, {
        case_context: case_context || sampleContext || {},
        rules_yaml: rules_yaml || yamlContent,
        version,
      });
      return res.data;
    },
  });
}
