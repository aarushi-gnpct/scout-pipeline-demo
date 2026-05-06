import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-example',
  templateUrl: './example.component.html',
  styleUrls: ['./example.component.css']
})
export class ExampleComponent implements OnInit {

  title: string = 'My Example Component';

  constructor() {
  }

  ngOnInit(): void {
    console.log('Component initialized');
  }

  onClick(): void {
    console.log('Button clicked!');
  }

}
