import { openDB } from "idb";
import type { NetworkInput } from "./schema";
import type { Intervention } from "./solver";

export interface NetworkWorkspace {
  input: NetworkInput;
  patch: Intervention;
}
// Isolated from screening scenarios: schema/model meanings cannot be mixed.
const db = () =>
  openDB("grid-conductor-network-lab", 1, {
    upgrade(database) {
      database.createObjectStore("workspace");
    },
  });
export async function saveNetworkWorkspace(value: NetworkWorkspace): Promise<void> {
  const database = await db();
  try {
    await database.put("workspace", value, "current");
  } finally {
    database.close();
  }
}
export async function loadNetworkWorkspace(): Promise<NetworkWorkspace | undefined> {
  const database = await db();
  try {
    return (await database.get("workspace", "current")) as NetworkWorkspace | undefined;
  } finally {
    database.close();
  }
}
