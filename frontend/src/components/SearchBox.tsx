import { type FormEvent, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Icon } from "./Icon";

export function SearchBox() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [value, setValue] = useState(params.get("q") ?? "");

  function submit(event: FormEvent) {
    event.preventDefault();
    navigate(`/search?q=${encodeURIComponent(value.trim())}`);
  }

  return (
    <form className="search" role="search" onSubmit={submit}>
      <Icon name="search" />
      <input
        type="search"
        aria-label="Buscar canciones o artistas"
        placeholder="Buscar canciones o artistas"
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
    </form>
  );
}
