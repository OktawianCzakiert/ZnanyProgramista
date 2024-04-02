from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseNotFound, HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import cloudinary
import cloudinary.uploader

from accounts.forms import ProgrammerCreationModelForm, RatingForm, AvatarUploadForm
from accounts.models import ProgrammerProfile, Rating, CustomUser
from accounts.services.cloudinary import configure_cloudinary, generate_random_string


def programmers_list(request):
    programmers = ProgrammerProfile.objects.all()
    for programmer in programmers:
        programmer.average_rating = programmer.average_rating()
    ctx = {
        "programmers": programmers,
    }

    return render(
        request,
        template_name="accounts/programmers_list.html",
        context=ctx,
    )


@login_required
def programmer_detail(request, id):
    rated = False
    try:
        programmer = get_object_or_404(ProgrammerProfile, id=id)
        programmer.average_rating = programmer.average_rating()
        users_ratings = Rating.objects.filter(user_id=request.user.id).first()
        if users_ratings:
            rated = True
    except ProgrammerProfile.DoesNotExist:
        return HttpResponseNotFound("Page not found")
    if request.user.id == programmer.user_id.id:
        user = request.user.id
    else:
        user = None

    ctx = {
        "programmer": programmer,
        "user": user,
        "rated": rated,
    }

    return render(
        request,
        template_name="accounts/programmer_detail.html",
        context=ctx,
    )


@login_required
def programmer_create_form(request):
    print(request.user.is_dev)
    if request.user.is_dev:
        return HttpResponseForbidden("You have already created a programmer account")
    form = ProgrammerCreationModelForm(request.POST or None)
    if request.method == 'GET':
        ctx = {
            "form": form,
        }
        return render(
            request,
            template_name='accounts/programmer_create_model_form.html',
            context=ctx,
        )

    elif request.method == 'POST':
        form = ProgrammerCreationModelForm(request.POST)
        if form.is_valid():
            programmer = form.save(commit=False)
            programmer.user_id = request.user
            programmer.save()
            request.user.is_dev = True
            request.user.save()
            messages.success(
                request,
                message=f"Programmer {programmer.user_id.first_name} {programmer.user_id.last_name} has been successfully created",
            )

            return redirect(f'/programmers/detail/{programmer.id}')
        ctx = {
            "form": form,
        }
        messages.error(
            request,
            message="Something went wrong",
        )
        return render(
            request,
            template_name='accounts/programmer_create_model_form.html',
            context=ctx,
        )


@login_required
def programmer_update_model_form(request, id):
    programmer = get_object_or_404(ProgrammerProfile, id=id)

    if request.user.id != programmer.user_id.id:
        raise PermissionDenied("You do not have permission to edit this index.")

    if request.method == "GET":
        form = ProgrammerCreationModelForm(instance=programmer)
        ctx = {
            "form": form,
            "programmer": programmer,
        }
        return render(
            request,
            template_name="accounts/programmer_update_model_form.html",
            context=ctx,
        )
    if request.method == "POST":
        form = ProgrammerCreationModelForm(request.POST, instance=programmer)

        if form.is_valid():
            form.save()
            ctx = {
                "form": form,
                "programmer": programmer,
            }
            messages.success(
                request,
                message=f"Programmer {programmer.user_id.first_name} {programmer.user_id.last_name} has been successfully edited",
            )
            return render(
                request,
                template_name="accounts/programmer_detail.html",
                context=ctx,
            )

        ctx = {
            "form": form,
            "programmer": programmer,
        }
        messages.error(
            request,
            message="Something went wrong",
        )

        return render(
            request,
            template_name="accounts/programmer_update_model_form.html",
            context=ctx,
        )


@login_required
def programmer_delete_confirm(request, id):
    programmer = get_object_or_404(ProgrammerProfile, id=id)

    if request.user.id != programmer.user_id.id:
        raise PermissionDenied("You do not have permission to delete this index.")
    if request.method == "GET":
        ctx = {
            "programmer": programmer,
        }
        return render(
            request,
            template_name="accounts/programmer_delete_confirm.html",
            context=ctx,
        )

    if request.method == "POST":
        programmer.delete()
        request.user.is_dev = False
        request.user.save()
        messages.success(
            request,
            message=f"Programmer {programmer.user_id.first_name} {programmer.user_id.last_name} has been successfully deleted",
        )

        return redirect("programmers_list")


@login_required
def rate_programmer(request, id):
    programmer = get_object_or_404(ProgrammerProfile, id=id)

    if request.method == "GET":
        existing_rating = Rating.objects.filter(programmer=programmer, user=request.user).first()
        if existing_rating:
            form = RatingForm(initial={'rating': existing_rating.rating})
        else:
            form = RatingForm()
        ctx = {
            "programmer": programmer,
            "form": form,
        }
        return render(
            request,
            template_name='accounts/rate_programmer.html',
            context=ctx,
        )

    if request.method == 'POST':
        form = RatingForm(request.POST)
        if request.user.id == programmer.user_id.id:
            user = request.user.id
        else:
            user = None

        if form.is_valid():
            user_rating = form.cleaned_data['rating']
            existing_rating = Rating.objects.filter(programmer=programmer, user=request.user).first()
            if existing_rating:
                existing_rating.rating = user_rating
                existing_rating.save()
                messages.success(
                    request,
                    message="Your rating has been updated."
                )
            else:
                new_rating = Rating.objects.create(programmer=programmer, user=request.user, rating=user_rating)
                new_rating.save()
                messages.success(
                    request,
                    message="Your rating has been submitted.",
                )

            ctx = {
                "form": form,
                "programmer": programmer,
                "user": user,
            }

            return render(
                request,
                template_name="accounts/programmer_detail.html",
                context=ctx,
            )

        else:
            messages.error(
                request,
                message="Invalid form submission."
            )
            return redirect('accounts/programmers_list')


@login_required
def upload_avatar(request, id):
    user = get_object_or_404(CustomUser, id=id)

    if request.user.id != user.id:
        raise PermissionDenied("You do not have permission to upload/ update this avatar.")

    if request.method == "GET":
        form = AvatarUploadForm()
        ctx = {
            "form": form,
            "user": user,
        }
        return render(
            request,
            template_name='accounts/programmer_avatar_update.html',
            context=ctx,
        )

    if request.method == 'POST':
        form = AvatarUploadForm(request.POST, request.FILES)

        if form.is_valid():

            configure_cloudinary()
            picture_name = generate_random_string()
            uploaded_file = request.FILES['avatar']
            r = cloudinary.uploader.upload(uploaded_file, public_id=f'avatars/{picture_name}', overwrite=True)
            version = r.get('version')
            if version:
                src_url = cloudinary.CloudinaryImage(f'avatars/{picture_name}') \
                    .build_url(background="auto", gravity="auto", width=250, height=250, crop='fill_pad', version=version)
                user.avatar = src_url
                user.save()
                messages.success(
                    request,
                    message="Your avatar has been successfully uploaded."
                )
                return redirect('programmer_detail', id=id)

        else:
            messages.error(
                request,
                message="Invalid form submission."
            )

        ctx = {
                "form": form,
                "user": user,
            }

        return render(
            request,
            template_name="accounts/programmer_avatar_update.html",
            context=ctx,
        )