from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from cinema.models import (
    Genre,
    Actor,
    CinemaHall,
    Movie,
    MovieSession,
    Ticket,
    Order
)


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ("id", "name")


class ActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actor
        fields = ("id", "first_name", "last_name", "full_name")


class CinemaHallSerializer(serializers.ModelSerializer):
    class Meta:
        model = CinemaHall
        fields = ("id", "name", "rows", "seats_in_row", "capacity")


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ("id", "title", "description", "duration", "genres", "actors")


class MovieListSerializer(MovieSerializer):
    genres = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    actors = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="full_name"
    )


class MovieDetailSerializer(MovieSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    actors = ActorSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = ("id", "title", "description", "duration", "genres", "actors")


class MovieSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall")


class MovieSessionListSerializer(MovieSessionSerializer):
    movie_title = serializers.CharField(source="movie.title", read_only=True)
    cinema_hall_name = serializers.CharField(
        source="cinema_hall.name", read_only=True
    )
    cinema_hall_capacity = serializers.IntegerField(
        source="cinema_hall.capacity", read_only=True
    )

    class Meta:
        model = MovieSession
        fields = (
            "id",
            "show_time",
            "movie_title",
            "cinema_hall_name",
            "cinema_hall_capacity",
        )


class MovieSessionDetailSerializer(MovieSessionSerializer):
    movie = MovieListSerializer(many=False, read_only=True)
    cinema_hall = CinemaHallSerializer(many=False, read_only=True)

    class Meta:
        model = MovieSession
        fields = ("id", "show_time", "movie", "cinema_hall")


class TicketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ticket
        fields = ("id", "movie_session", "row", "seat")
        validators = [
            UniqueTogetherValidator(
                queryset=Ticket.objects.all(),
                fields=["movie_session", "row", "seat"]
            )
        ]

    def validate(self, attrs):
        Ticket.validate_seat(
            attrs["row"],
            attrs["seat"],
            attrs["movie_session"].cinema_hall.rows,
            attrs["movie_session"].cinema_hall.seats_in_row,
            serializers.ValidationError
        )
        # if not (1 <= attrs["row"] <= attrs["movie_session"].cinema_hall.rows):
        #     raise serializers.ValidationError(
        #         {
        #             "row": [
        #                 f"row number must be in available range: (1, rows): "
        #                 f"(1, {attrs["movie_session"].cinema_hall.rows})"
        #             ]
        #         }
        #     )
        # if not (1 <= attrs["seat"] <= attrs["movie_session"].cinema_hall.seats_in_row):
        #     raise serializers.ValidationError(
        #         {
        #             "seat": [
        #                 f"seat number must be in available range: "
        #                 f"(1, seats_in_row): "
        #                 f"(1, {attrs["movie_session"].cinema_hall.seats_in_row})"
        #             ]
        #         }
        #     )

class OrderSerializer(serializers.ModelSerializer):

    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order
