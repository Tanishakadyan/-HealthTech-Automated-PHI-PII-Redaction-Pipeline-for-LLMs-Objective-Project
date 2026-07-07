import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "@/lib/api/redaction";

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 20_000,
    retry: 1,
    staleTime: 5_000,
  });
}
