const MAX = 140;

export function DedicationEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const left = MAX - value.length;
  return (
    <label className="dedication">
      Dedicatoria (opcional)
      <textarea
        rows={3}
        maxLength={MAX}
        value={value}
        placeholder="para que no te duermas manejando"
        aria-describedby="dedication-left"
        onChange={(event) => onChange(event.target.value)}
      />
      <small id="dedication-left">{left === 1 ? "Queda 1 carácter" : `Quedan ${left} caracteres`}</small>
    </label>
  );
}
