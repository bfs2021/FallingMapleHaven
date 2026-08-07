export function findAdminPluginByType(response, type) {
  return response?.data?.results?.find(plugin => plugin.type === type) ?? null
}
