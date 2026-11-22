import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createGroup,
  deleteGroup,
  listGroups,
  removeGroupMember,
  updateGroup,
  upsertGroupMember,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { GroupItem } from "../types";


export default function GroupsPage() {
  const { currentUser } = useAuth();
  const { showToast } = useToast();
  const [groups, setGroups] = useState<GroupItem[]>([]);
  const [selected, setSelected] = useState<GroupItem | null>(null);
  const [loading, setLoading] = useState(true);


  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");


  const [memberUserId, setMemberUserId] = useState("");
  const [canCreate, setCanCreate] = useState(true);
  const [canEdit, setCanEdit] = useState(false);
  const [canAssign, setCanAssign] = useState(false);


  const [renameValue, setRenameValue] = useState("");


  const load = async (selectId?: number) => {
    setLoading(true);
    try {
      const data = await listGroups();
      setGroups(data);
      const next = data.find((g) => g.id === (selectId ?? selected?.id)) || data[0] || null;
      setSelected(next);
      setRenameValue(next?.name || "");
    } catch (err: any) {
      showToast(err?.message || "Failed to load groups", "error");
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    load();
  }, []);


  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const created = await createGroup({ name: newName.trim(), description: newDesc.trim() || undefined });
      setNewName("");
      setNewDesc("");
      showToast(`Group "${created.name}" created`, "success");
      await load(created.id);
    } catch (err: any) {
      showToast(err?.message || "Failed to create group", "error");
    }
  };


  const handleRename = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !renameValue.trim()) return;
    try {
      const updated = await updateGroup(selected.id, { name: renameValue.trim(), description: selected.description || undefined });
      showToast("Group renamed", "success");
      await load(updated.id);
    } catch (err: any) {
      showToast(err?.message || "Only the owner can rename this group", "error");
    }
  };


  const handleDeleteGroup = async () => {
    if (!selected || !window.confirm(`Delete group "${selected.name}"?`)) return;
    try {
      await deleteGroup(selected.id);
      showToast("Group deleted", "success");
      setSelected(null);
      await load();
    } catch (err: any) {
      showToast(err?.message || "Only the owner can delete this group", "error");
    }
  };


  const handleAddMember = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !memberUserId) return;
    try {
      const updated = await upsertGroupMember(selected.id, {
        user_id: Number(memberUserId),
        can_create: canCreate,
        can_edit: canEdit,
        can_assign: canAssign,
      });
      setMemberUserId("");
      showToast("Member permissions saved", "success");
      await load(updated.id);
    } catch (err: any) {
      showToast(err?.message || "Failed to update member", "error");
    }
  };


  const handleRemoveMember = async (uid: number) => {
    if (!selected) return;
    try {
      const updated = await removeGroupMember(selected.id, uid);
      showToast("Member removed", "success");
      await load(updated.id);
    } catch (err: any) {
      showToast(err?.message || "Failed to remove member", "error");
    }
  };


  const isOwner =
    selected && currentUser && selected.owner_id === currentUser.id;


  return (
    <div className="container">
      <h1>Shared Triage Groups</h1>
      <p className="muted">Collaborate on vulnerability reports with per-member permissions (Create, Edit, Assign).</p>


      <form className="card" onSubmit={handleCreate} style={{ marginBottom: "1.5rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <input
          placeholder="New group name..."
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          required
        />
        <input
          placeholder="Description (optional)"
          value={newDesc}
          onChange={(e) => setNewDesc(e.target.value)}
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" type="submit">+ Create Group</button>
      </form>


      {loading ? (
        <p>Loading groups...</p>
      ) : groups.length === 0 ? (
        <div className="card">You are not in any groups yet. Create one above!</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "1.25rem", alignItems: "start" }}>
          <div className="card">
            <h3>Your Groups</h3>
            {groups.map((g) => (
              <button
                key={g.id}
                onClick={() => {
                  setSelected(g);
                  setRenameValue(g.name);
                }}
                className={`btn ${selected?.id === g.id ? "btn-primary" : "btn-secondary"}`}
                style={{ width: "100%", textAlign: "left", marginBottom: "0.5rem" }}
              >
                {g.name} {g.owner_id === currentUser?.id ? "(Owner)" : ""}
              </button>
            ))}
          </div>


          {selected && (
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
                <div>
                  <h2>{selected.name}</h2>
                  <p className="muted">Owner: {selected.owner_email} • {selected.description || "No description"}</p>
                </div>
                <Link to={`/reports/new?group_id=${selected.id}`} className="btn btn-primary">
                  + Submit Group Report
                </Link>
              </div>


              {isOwner && (
                <form onSubmit={handleRename} style={{ display: "flex", gap: "0.5rem", margin: "1rem 0" }}>
                  <input value={renameValue} onChange={(e) => setRenameValue(e.target.value)} />
                  <button className="btn btn-secondary" type="submit">Rename</button>
                  <button className="btn btn-danger" type="button" onClick={handleDeleteGroup}>
                    Delete Group
                  </button>
                </form>
              )}


              <h3 style={{ marginTop: "1rem" }}>Members & Permissions</h3>
              <table className="table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Create</th>
                    <th>Edit</th>
                    <th>Assign</th>
                    {isOwner && <th>Action</th>}
                  </tr>
                </thead>
                <tbody>
                  {selected.members.map((m) => (
                    <tr key={m.user_id}>
                      <td>{m.name} ({m.email}) [ID: {m.user_id}]</td>
                      <td>{m.can_create ? "✅" : "—"}</td>
                      <td>{m.can_edit ? "✅" : "—"}</td>
                      <td>{m.can_assign ? "✅" : "—"}</td>
                      {isOwner && (
                        <td>
                          <button className="btn btn-danger btn-sm" onClick={() => handleRemoveMember(m.user_id)}>
                            Remove
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                  {selected.members.length === 0 && (
                    <tr><td colSpan={5} className="muted">No members added yet.</td></tr>
                  )}
                </tbody>
              </table>


              {isOwner && (
                <form onSubmit={handleAddMember} style={{ marginTop: "1rem", display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
                  <input
                    type="number"
                    placeholder="User ID"
                    value={memberUserId}
                    onChange={(e) => setMemberUserId(e.target.value)}
                    style={{ width: 100 }}
                    required
                  />
                  <label><input type="checkbox" checked={canCreate} onChange={(e) => setCanCreate(e.target.checked)} /> Create</label>
                  <label><input type="checkbox" checked={canEdit} onChange={(e) => setCanEdit(e.target.checked)} /> Edit</label>
                  <label><input type="checkbox" checked={canAssign} onChange={(e) => setCanAssign(e.target.checked)} /> Assign</label>
                  <button className="btn btn-primary" type="submit">Add / Update Member</button>
                </form>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
