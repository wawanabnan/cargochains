<form method="post"
      action="{% url 'core:profile_modal_submit' %}"
      enctype="multipart/form-data"
      id="profileModalForm">
  {% csrf_token %}

  {% if form.non_field_errors %}
    <div class="alert alert-danger py-2">{{ form.non_field_errors }}</div>
  {% endif %}

  <div class="row g-2">
    <div class="col-md-6">
      <label class="form-label small mb-1">First Name</label>
      {{ form.first_name }}
      {% if form.first_name.errors %}<div class="text-danger small mt-1">{{ form.first_name.errors }}</div>{% endif %}
    </div>
    <div class="col-md-6">
      <label class="form-label small mb-1">Last Name</label>
      {{ form.last_name }}
      {% if form.last_name.errors %}<div class="text-danger small mt-1">{{ form.last_name.errors }}</div>{% endif %}
    </div>
  </div>

  <div class="mt-2">
    <label class="form-label small mb-1">Username</label>
    {{ form.username }}
    {% if form.username.errors %}<div class="text-danger small mt-1">{{ form.username.errors }}</div>{% endif %}
    <div class="text-secondary small mt-1">Username harus unik.</div>
  </div>

  <hr class="my-3">

  <div class="mb-2">
    <label class="form-label small mb-1">Title</label>
    {{ form.title }}
    {% if form.title.errors %}<div class="text-danger small mt-1">{{ form.title.errors }}</div>{% endif %}
  </div>

  <div class="mb-2">
    <label class="form-label small mb-1">Signature (PNG/JPG)</label>
    {{ form.signature }}
    {% if form.signature.errors %}<div class="text-danger small mt-1">{{ form.signature.errors }}</div>{% endif %}
    <div class="text-secondary small mt-1">Max 1MB. Rekomendasi: PNG background transparan.</div>
  </div>

  {% if request.user.profile.signature %}
    <div class="border rounded p-2 mt-2">
      <div class="text-secondary small mb-1">Current Signature</div>
      <img src="{{ request.user.profile.signature.url }}" alt="signature"
           style="height:60px; object-fit:contain;">
    </div>
  {% endif %}

  <div class="d-flex justify-content-end gap-2 mt-3">
    <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">Close</button>
    <button type="submit" class="btn btn-primary btn-sm">
      <i class="bi bi-save me-1"></i> Save
    </button>
  </div>
</form>
